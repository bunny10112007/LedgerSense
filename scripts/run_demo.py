#!/usr/bin/env python3
"""Execute end-to-end golden demo run on LedgerSense."""

from __future__ import annotations

import hashlib
import shutil
import sys
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

# Add backend/src to sys.path so ledgersense package is importable
repo_root = Path(__file__).resolve().parents[1]
backend_src = repo_root / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from reset_demo import reset_demo
from sqlmodel import Session, select

from ledgersense.core.config import settings
from ledgersense.db.models import (
    DocumentRecord,
    JournalEntryRecord,
    MatchRecord,
    ReceiptRecord,
    RiskFlagRecord,
    RunRecord,
)
from ledgersense.db.repository import Repository
from ledgersense.db.session import engine
from ledgersense.domain.models import RunConfig
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.pipeline.orchestrator import process_run


def run_demo() -> None:
    start_time = time.perf_counter()
    # Force replay mode for fast deterministic offline execution
    settings.LLM_MODE = "replay"

    print("==================================================")
    print("      LedgerSense - Golden Demo Pipeline          ")
    print("==================================================")

    # 1. Reset database and uploads
    reset_demo()

    run_id = "run:2025-26-demo"
    period_start = date(2025, 4, 1)
    period_end = date(2026, 3, 31)

    with Session(engine) as session:
        # 2. Create Run Record
        cfg = RunConfig(
            period_start=period_start,
            period_end=period_end,
            tax_regime_choice="old",
            cash_limit=Decimal("10000.00"),
            date_window_days=3,
            amount_tolerance=Decimal("5.00"),
        )
        run_record = RunRecord(
            id=run_id,
            period_start=cfg.period_start,
            period_end=cfg.period_end,
            regime=cfg.regime,
            status="CREATED",
            config_json=cfg.model_dump_json(),
            created_at=datetime.now(UTC),
        )
        session.add(run_record)
        session.commit()
        print(f"[+] Initialized run: {run_id} (Regime: {cfg.regime})")

        # 3. Ingest Documents
        golden_receipts_dir = repo_root / "data" / "golden" / "receipts"
        safe_run_dir = run_id.replace(":", "_")
        upload_dir = repo_root / "data" / "uploads" / safe_run_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        png_files = sorted(golden_receipts_dir.glob("*.png"))
        if not png_files:
            raise FileNotFoundError(f"No receipt images found in {golden_receipts_dir}")

        for p in png_files:
            dest_file = upload_dir / p.name
            shutil.copy2(p, dest_file)
            content = p.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()

            doc_record = DocumentRecord(
                id=f"doc:{p.stem.lower()}",
                run_id=run_id,
                filename=p.name,
                file_hash=file_hash,
                mime="image/png",
                extraction_status="PENDING",
            )
            session.add(doc_record)

        session.commit()
        print(f"[+] Ingested {len(png_files)} receipt documents.")

        # 4. Ingest Bank Statement CSV
        bank_csv_path = repo_root / "data" / "golden" / "bank.csv"
        if not bank_csv_path.exists():
            raise FileNotFoundError(f"Bank CSV not found at {bank_csv_path}")

        bank_lines = parse_bank_csv(bank_csv_path.read_bytes(), run_id=run_id)
        repo = Repository(session)
        repo.save_bank_lines(bank_lines)
        print(f"[+] Ingested {len(bank_lines)} bank statement lines.")

        # 5. Process Run Pipeline
        print(
            "[*] Processing pipeline (extract -> validate -> match -> detect risks -> draft journals)..."
        )
        final_status = process_run(run_id, session)

        # 6. Gather and Print Summary
        receipts = list(
            session.exec(
                select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)
            ).all()
        )
        matches = list(
            session.exec(select(MatchRecord).where(MatchRecord.run_id == run_id)).all()
        )
        flags = list(
            session.exec(
                select(RiskFlagRecord).where(RiskFlagRecord.run_id == run_id)
            ).all()
        )
        journals = list(
            session.exec(
                select(JournalEntryRecord).where(JournalEntryRecord.run_id == run_id)
            ).all()
        )

        high_flags = [f for f in flags if f.severity == "HIGH"]
        med_flags = [f for f in flags if f.severity == "MEDIUM"]
        low_flags = [f for f in flags if f.severity == "LOW"]

        elapsed = time.perf_counter() - start_time

        print("\n--------------------------------------------------")
        print("                 DEMO RUN SUMMARY                 ")
        print("--------------------------------------------------")
        print(f"Run ID:                 {run_id}")
        print(f"Final Run Status:       {final_status}")
        print(f"Documents Ingested:     {len(png_files)}")
        print(f"Receipts Extracted:     {len(receipts)}")
        print(f"Matches Formed:         {len(matches)}")
        print(f"Total Risk Flags:       {len(flags)}")
        print(f"  - HIGH Severity:      {len(high_flags)} (Gate Blocking)")
        for hf in high_flags:
            print(f"      * [{hf.rule_id}] {hf.suggested_action}")
        print(f"  - MEDIUM Severity:    {len(med_flags)}")
        print(f"  - LOW Severity:       {len(low_flags)}")
        print(f"Draft Journal Entries:  {len(journals)}")
        print(f"Execution Time:         {elapsed:.2f} seconds")
        print("--------------------------------------------------")
        if elapsed < 20.0:
            print(f"[OK] Completed in {elapsed:.2f}s (< 20s limit).")
        else:
            print(f"[WARNING] Execution took {elapsed:.2f}s (exceeded 20s).")


if __name__ == "__main__":
    run_demo()
