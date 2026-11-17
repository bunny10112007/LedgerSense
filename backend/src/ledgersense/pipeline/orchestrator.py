from __future__ import annotations

<<<<<<< HEAD
import logging
from pathlib import Path

from sqlmodel import Session, select

from ledgersense.core.config import settings
from ledgersense.db.models import (
    BankLineRecord,
    DocumentRecord,
    MatchRecord,
    ReceiptRecord,
    RunRecord,
)
from ledgersense.db.repository import Repository
from ledgersense.domain.models import BankLine, Match, Receipt, RunConfig, RunStatus
from ledgersense.extraction.extractor import ReceiptExtractor
from ledgersense.matching.matcher import match as match_receipts_to_bank
from ledgersense.pipeline.adapters import (
    build_draft_journal_entries,
    detect_risk_flags,
    validate_gstin,
)
from ledgersense.pipeline.state_machine import transition_run_status

logger = logging.getLogger(__name__)


def process_run(run_id: str, session: Session) -> RunStatus:
    """Execute complete deterministic pipeline for a run matching Section 4 & 7."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    cfg = RunConfig.model_validate_json(run.config_json)
    repo = Repository(session)

    # 1. Extraction Stage: CREATED -> EXTRACTED
    if run.status == "CREATED":
        transition_run_status(run_id, "EXTRACTED", session)
        documents = list(
            session.exec(
                select(DocumentRecord).where(DocumentRecord.run_id == run_id)
            ).all()
        )
        extractor = ReceiptExtractor()
        extracted_receipts: list[Receipt] = []

        safe_run_dir = run_id.replace(":", "_")
        uploads_dir = settings.uploads_dir / safe_run_dir
        golden_receipts_dir = settings.golden_dir / "receipts"

        for idx, doc in enumerate(documents):
            # Locate file on disk: check uploads dir, then golden receipts dir, then raw filename
            candidate_paths = [
                uploads_dir / doc.filename,
                settings.uploads_dir / run_id / doc.filename,
                golden_receipts_dir / doc.filename,
                Path(doc.filename),
            ]
            file_path = next((p for p in candidate_paths if p.exists()), None)
            if not file_path:
                logger.error("Document file not found for %s: %s", doc.id, doc.filename)
                continue

            stem = file_path.stem.lower()
            rcpt_code = ("G" + stem[1:]) if stem.startswith("g") else f"{idx + 1:04d}"
            rcpt_id = f"rcpt:{rcpt_code}"

            receipt = extractor.extract_document(
                path=file_path,
                receipt_id=rcpt_id,
                source_file=doc.filename,
                run_id=run_id,
                session=session,
            )
            extracted_receipts.append(receipt)
            doc.extraction_status = receipt.extraction_status
            session.add(doc)

        if extracted_receipts:
            repo.save_receipts(extracted_receipts)
        session.commit()

    # 2. Validation Stage: EXTRACTED -> VALIDATED
    run = session.get(RunRecord, run_id)
    assert run is not None
    if run.status == "EXTRACTED":
        transition_run_status(run_id, "VALIDATED", session)
        receipt_records = list(
            session.exec(
                select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)
            ).all()
        )
        for r_rec in receipt_records:
            r = Receipt.model_validate_json(r_rec.payload_json)
            if r.vendor_gstin:
                gstin_res = validate_gstin(r.vendor_gstin)
                if not gstin_res.ok and gstin_res.reason:
                    r.check_messages.append(f"GSTIN validation: {gstin_res.reason}")
                    r_rec.payload_json = r.model_dump_json()
                    session.add(r_rec)
        session.commit()

    # 3. Matching Stage: VALIDATED -> MATCHED
    run = session.get(RunRecord, run_id)
    assert run is not None
    if run.status == "VALIDATED":
        transition_run_status(run_id, "MATCHED", session)
        receipt_records = list(
            session.exec(
                select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)
            ).all()
        )
        receipts = [
            Receipt.model_validate_json(rec.payload_json) for rec in receipt_records
        ]

        bank_records = list(
            session.exec(
                select(BankLineRecord).where(BankLineRecord.run_id == run_id)
            ).all()
        )
        bank_lines = [
            BankLine(
                id=b.id,
                run_id=b.run_id,
                txn_date=b.txn_date,
                narration=b.narration,
                debit=b.debit,  # type: ignore[arg-type]
                credit=b.credit,  # type: ignore[arg-type]
                balance=b.balance,  # type: ignore[arg-type]
                ref_no=b.ref_no,
            )
            for b in bank_records
        ]

        matches = match_receipts_to_bank(receipts, bank_lines, cfg)
        repo.save_matches(matches)
        session.commit()

    # 4. Risk Detection Stage: MATCHED -> RISK_DONE
    run = session.get(RunRecord, run_id)
    assert run is not None
    if run.status == "MATCHED":
        transition_run_status(run_id, "RISK_DONE", session)
        receipt_records = list(
            session.exec(
                select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)
            ).all()
        )
        receipts = [
            Receipt.model_validate_json(rec.payload_json) for rec in receipt_records
        ]

        bank_records = list(
            session.exec(
                select(BankLineRecord).where(BankLineRecord.run_id == run_id)
            ).all()
        )
        bank_lines = [
            BankLine(
                id=b.id,
                run_id=b.run_id,
                txn_date=b.txn_date,
                narration=b.narration,
                debit=b.debit,  # type: ignore[arg-type]
                credit=b.credit,  # type: ignore[arg-type]
                balance=b.balance,  # type: ignore[arg-type]
                ref_no=b.ref_no,
            )
            for b in bank_records
        ]

        match_records = list(
            session.exec(select(MatchRecord).where(MatchRecord.run_id == run_id)).all()
        )
        matches = [
            Match(
                id=m.id,
                run_id=m.run_id,
                receipt_id=m.receipt_id,
                bank_line_id=m.bank_line_id,
                score=m.score,
                kind=m.kind,  # type: ignore[arg-type]
                date_delta_days=m.date_delta_days,
                amount_delta=m.amount_delta,  # type: ignore[arg-type]
            )
            for m in match_records
        ]

        flags = detect_risk_flags(receipts, bank_lines, matches, cfg, session)
        repo.save_risk_flags(flags)

        # Build initial balanced DRAFT journal entries
        entries = build_draft_journal_entries(run_id, receipts, bank_lines, flags)
        repo.save_journal_entries(entries)
        session.commit()

    # 5. Review Stage: RISK_DONE -> AWAITING_REVIEW or APPROVED
    run = session.get(RunRecord, run_id)
    assert run is not None
    if run.status == "RISK_DONE":
        flags = repo.get_risk_flags(run_id)
        has_open_high = any(f.severity == "HIGH" and f.status == "OPEN" for f in flags)
        if has_open_high:
            transition_run_status(run_id, "AWAITING_REVIEW", session)
            return "AWAITING_REVIEW"
        transition_run_status(run_id, "APPROVED", session)
        return "APPROVED"

    return run.status  # type: ignore[return-value]
=======
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session

from ledgersense.accounting.journal import build_entries, commit_entries
from ledgersense.audit.log import compute_payload_hash
from ledgersense.db.repository import Repository
from ledgersense.domain.models import AuditEvent, JournalEntry, Receipt, RiskFlag, Run
from ledgersense.extraction.extractor import ReceiptExtractor
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.matching.matcher import match
from ledgersense.pipeline.gate import can_commit, check_run_gate
from ledgersense.pipeline.state_machine import transition_run
from ledgersense.tax.risk_detectors import detect_all
from ledgersense.tax.rules_engine import load_rules


class GateBlockedError(ValueError):
    """Raised when commit_run is attempted while HIGH severity risk flags remain OPEN."""

    def __init__(self, open_high_flags: list[RiskFlag]) -> None:
        self.open_high_flags = open_high_flags
        rules = [f.rule_id for f in open_high_flags]
        super().__init__(
            f"Commit blocked: {len(open_high_flags)} HIGH severity risk flags remain OPEN ({rules})."
        )


def process_run(
    session: Session,
    run_id: str,
    receipt_paths: list[Path] | None = None,
    bank_csv_path: Path | None = None,
) -> Run:
    """Execute the end-to-end ingestion and reconciliation pipeline for a run.

    Pipeline milestones:
    CREATED -> EXTRACTED -> VALIDATED -> MATCHED -> RISK_DONE -> AWAITING_REVIEW | APPROVED
    """
    repo = Repository(session)
    run = repo.get_domain_run(run_id)
    if not run:
        raise ValueError(f"Run '{run_id}' not found")

    try:
        # Step 1: Document Extraction & Validation
        receipts: list[Receipt] = []
        if receipt_paths:
            extractor = ReceiptExtractor()
            for p in sorted(receipt_paths):
                stem = p.stem.lower()
                rcpt_code = ("G" + stem[1:]) if stem.startswith("g") else stem
                rcpt_id = f"rcpt:{rcpt_code}"
                receipt = extractor.extract_document(
                    path=p,
                    receipt_id=rcpt_id,
                    source_file=f"receipts/{p.name}",
                    run_id=run_id,
                    session=session,
                )
                receipts.append(receipt)

                # Record extraction audit event
                evt = AuditEvent(
                    id=f"evt:{uuid4().hex[:12]}",
                    ts=datetime.now(UTC),
                    run_id=run_id,
                    actor="system",
                    action="EXTRACTION",
                    entity_id=receipt.id,
                    reason=f"Extracted document {receipt.source_file}",
                    payload_hash=compute_payload_hash(
                        {"receipt_id": receipt.id, "file_hash": receipt.file_hash}
                    ),
                )
                repo.append_audit_event(evt)

            repo.save_receipts(receipts)
        else:
            receipts = repo.get_domain_receipts(run_id)

        transition_run(session, run_id, "EXTRACTED")
        transition_run(session, run_id, "VALIDATED")

        # Step 2: Bank Statement Ingestion & Matching
        if bank_csv_path:
            bank_lines = parse_bank_csv(bank_csv_path, run_id=run_id)
            repo.save_bank_lines(bank_lines)
        else:
            bank_lines = repo.get_domain_bank_lines(run_id)

        matches = match(receipts=receipts, bank_lines=bank_lines, cfg=run.config)
        repo.save_matches(matches)
        transition_run(session, run_id, "MATCHED")

        # Step 3: Statutory & Audit Risk Detection
        rules = load_rules()
        flags = detect_all(
            receipts=receipts,
            matches=matches,
            bank_lines=bank_lines,
            cfg=run.config,
            rules=rules,
        )
        repo.save_risk_flags(flags)
        transition_run(session, run_id, "RISK_DONE")

        # Step 4: Initial Journal Drafts & Gate Review Stepper
        entries = build_entries(
            receipts=receipts,
            matches=matches,
            flags=flags,
            cfg=run.config,
            bank_lines=bank_lines,
        )
        repo.save_journal_entries(entries)

        _can_commit_allowed, open_high = can_commit(flags)
        if open_high:
            final_run = transition_run(
                session,
                run_id,
                "AWAITING_REVIEW",
                reason=f"{len(open_high)} HIGH severity risk flags require auditor review",
            )
        else:
            final_run = transition_run(
                session,
                run_id,
                "APPROVED",
                reason="Zero HIGH severity risk flags require review",
            )

        return final_run

    except Exception as exc:
        # On unrecoverable error, transition run to FAILED and re-raise
        try:
            current_run = repo.get_run(run_id)
            if current_run and current_run.status != "FAILED":
                transition_run(session, run_id, "FAILED", reason=str(exc))
        except (ValueError, RuntimeError):
            pass
        raise


def commit_run(
    session: Session,
    run_id: str,
    auditor_id: str = "auditor-a",
) -> list[JournalEntry]:
    """Execute the human sign-off gate to commit a run and finalize journal entries.

    Raises GateBlockedError if any HIGH severity risk flag remains OPEN.
    Transitions run status to COMMITTED and records an AuditEvent.
    """
    is_allowed, open_high = check_run_gate(session, run_id)
    if not is_allowed:
        raise GateBlockedError(open_high)

    repo = Repository(session)
    run = repo.get_domain_run(run_id)
    if not run:
        raise ValueError(f"Run '{run_id}' not found")

    # If run is in AWAITING_REVIEW, transition to APPROVED first
    if run.status == "AWAITING_REVIEW":
        run = transition_run(
            session=session,
            run_id=run_id,
            target="APPROVED",
            actor=auditor_id,
            reason="All HIGH severity risk flags approved by auditor",
        )

    receipts = repo.get_domain_receipts(run_id)
    matches = repo.get_domain_matches(run_id)
    flags = repo.get_domain_risk_flags(run_id)
    bank_lines = repo.get_domain_bank_lines(run_id)

    # Re-build entries with updated flag decisions and commit
    draft_entries = build_entries(
        receipts=receipts,
        matches=matches,
        flags=flags,
        cfg=run.config,
        bank_lines=bank_lines,
    )
    committed_entries = commit_entries(draft_entries, flags)

    # Persist updated committed entries in DB
    repo.clear_journal_entries(run_id)
    repo.save_journal_entries(committed_entries)

    # Transition run to COMMITTED
    transition_run(
        session=session,
        run_id=run_id,
        target="COMMITTED",
        actor=auditor_id,
        reason=f"Committed {len(committed_entries)} journal entries",
    )

    # Record Audit Event
    evt = AuditEvent(
        id=f"evt:{uuid4().hex[:12]}",
        ts=datetime.now(UTC),
        run_id=run_id,
        actor=auditor_id,
        action="RUN_COMMITTED",
        entity_id=run_id,
        reason=f"Committed {len(committed_entries)} journal entries by {auditor_id}",
        payload_hash=compute_payload_hash(
            {
                "run_id": run_id,
                "entries_committed": len(committed_entries),
                "auditor_id": auditor_id,
            }
        ),
    )
    repo.append_audit_event(evt)

    return committed_entries
>>>>>>> 002af4b0f998fc47ba702aa7c12154a99ecd8744
