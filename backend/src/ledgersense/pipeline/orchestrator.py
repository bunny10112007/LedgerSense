from __future__ import annotations

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
