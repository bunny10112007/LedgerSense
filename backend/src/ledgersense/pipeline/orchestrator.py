from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from ledgersense.accounting.journal import build_entries, commit_entries
from ledgersense.audit.log import compute_payload_hash
from ledgersense.core.config import settings
from ledgersense.db.models import DocumentRecord
from ledgersense.db.repository import Repository
from ledgersense.domain.models import AuditEvent, JournalEntry, Receipt, RiskFlag, Run
from ledgersense.extraction.extractor import ReceiptExtractor
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.matching.matcher import match
from ledgersense.pipeline.gate import can_commit, check_run_gate
from ledgersense.pipeline.state_machine import transition_run
from ledgersense.tax.gstin import validate_gstin
from ledgersense.tax.risk_detectors import detect_all
from ledgersense.tax.rules_engine import load_rules

logger = logging.getLogger(__name__)


class GateBlockedError(ValueError):
    """Raised when commit_run is attempted while HIGH severity risk flags remain OPEN."""

    def __init__(self, open_high_flags: list[RiskFlag]) -> None:
        self.open_high_flags = open_high_flags
        rules = [f.rule_id for f in open_high_flags]
        super().__init__(
            f"Commit blocked: {len(open_high_flags)} HIGH severity risk flags remain OPEN ({rules})."
        )


def process_run(
    run_id: str | Session | None = None,
    session: Session | str | None = None,
    receipt_paths: list[Path] | None = None,
    bank_csv_path: Path | None = None,
    *args: Any,
    **kwargs: Any,
) -> Run:
    """Execute complete deterministic pipeline for a run matching Section 4 & 7.

    Supports both (run_id, session) and (session, run_id) argument conventions,
    as well as positional and keyword calls.
    """
    if isinstance(run_id, Session):
        session, run_id = run_id, session
    elif run_id is None and "session" in kwargs:
        session = kwargs.pop("session")
    if isinstance(session, str) and not isinstance(run_id, str):
        session, run_id = run_id, session

    if not isinstance(run_id, str) or not isinstance(session, Session):
        raise TypeError(
            f"process_run requires valid run_id (str) and session (Session), got run_id={type(run_id)}, session={type(session)}"
        )

    repo = Repository(session)
    run = repo.get_domain_run(run_id)
    if not run:
        raise ValueError(f"Run '{run_id}' not found")

    cfg = run.config

    try:
        # Step 1: Document Extraction & Validation
        receipts: list[Receipt] = []
        files_to_extract: list[Path] = []
        if receipt_paths:
            files_to_extract = list(receipt_paths)
        else:
            documents = repo.get_documents(run_id)
            safe_run_dir = run_id.replace(":", "_")
            uploads_dir = settings.uploads_dir / safe_run_dir
            golden_receipts_dir = settings.golden_dir / "receipts"

            for doc in documents:
                candidate_paths = [
                    uploads_dir / doc.filename,
                    settings.uploads_dir / run_id / doc.filename,
                    golden_receipts_dir / doc.filename,
                    Path(doc.filename),
                ]
                file_path = next((p for p in candidate_paths if p.exists()), None)
                if file_path:
                    files_to_extract.append(file_path)
                else:
                    logger.error("Document file not found for %s: %s", doc.id, doc.filename)

        if files_to_extract:
            extractor = ReceiptExtractor()
            for idx, file_path in enumerate(sorted(files_to_extract)):
                stem = file_path.stem.lower()
                rcpt_code = ("G" + stem[1:]) if stem.startswith("g") else f"{idx + 1:04d}"
                rcpt_id = f"rcpt:{rcpt_code}"

                receipt = extractor.extract_document(
                    path=file_path,
                    receipt_id=rcpt_id,
                    source_file=f"receipts/{file_path.name}",
                    run_id=run_id,
                    session=session,
                )
                receipts.append(receipt)

                # Update document status if matching DocumentRecord exists
                doc_rec = session.exec(
                    select(DocumentRecord)
                    .where(DocumentRecord.run_id == run_id)
                    .where(DocumentRecord.filename == file_path.name)
                ).first()
                if doc_rec:
                    doc_rec.extraction_status = receipt.extraction_status
                    session.add(doc_rec)

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
            session.commit()
        else:
            receipts = repo.get_domain_receipts(run_id)

        transition_run(session, run_id, "EXTRACTED")

        # Validate GSTINs
        for r in receipts:
            if r.vendor_gstin:
                validate_gstin(r.vendor_gstin)

        transition_run(session, run_id, "VALIDATED")

        # Step 2: Bank Statement Ingestion & Matching
        if bank_csv_path and bank_csv_path.exists():
            bank_lines = parse_bank_csv(bank_csv_path, run_id=run_id)
            repo.save_bank_lines(bank_lines)
        else:
            bank_lines = repo.get_domain_bank_lines(run_id)

        matches = match(receipts=receipts, bank_lines=bank_lines, cfg=cfg)
        repo.save_matches(matches)
        transition_run(session, run_id, "MATCHED")

        # Step 3: Statutory & Audit Risk Detection
        rules = load_rules()
        flags = detect_all(
            receipts=receipts,
            matches=matches,
            bank_lines=bank_lines,
            cfg=cfg,
            rules=rules,
        )
        repo.save_risk_flags(flags)
        transition_run(session, run_id, "RISK_DONE")

        # Step 4: Initial Journal Drafts & Gate Review Stepper
        entries = build_entries(
            receipts=receipts,
            matches=matches,
            flags=flags,
            cfg=cfg,
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
