from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ledgersense.core.config import settings
from ledgersense.domain.models import RunConfig
from ledgersense.extraction.extractor import ReceiptExtractor
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.matching.matcher import match


def test_golden_replay_extraction_and_matcher(monkeypatch: pytest.MonkeyPatch) -> None:
    """Golden acceptance test: Extract 16 golden receipts from cache in replay mode and run matcher against bank.csv."""
    # Ensure replay mode is active (strictly zero network calls)
    monkeypatch.setattr(settings, "LLM_MODE", "replay")

    golden_dir = Path(__file__).resolve().parents[3] / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    bank_csv_path = golden_dir / "bank.csv"
    answer_key_path = golden_dir / "answer_key.json"

    with open(answer_key_path, encoding="utf-8") as f:
        answer_key = json.load(f)

    # 1. Replay extraction of all 16 golden receipt images
    extractor = ReceiptExtractor()
    extracted_receipts = []

    # Map file stem to golden ID (e.g. g01 -> rcpt:G01, g15a -> rcpt:G15a)
    for png_path in sorted(receipts_dir.glob("*.png")):
        stem = png_path.stem.lower()
        if stem.startswith("g"):
            rcpt_code = "G" + stem[1:]
            rcpt_id = f"rcpt:{rcpt_code}"
        else:
            rcpt_id = f"rcpt:{stem}"

        receipt = extractor.extract_document(
            path=png_path,
            receipt_id=rcpt_id,
            source_file=f"receipts/{png_path.name}",
        )
        assert receipt.extraction_status in ("OK", "LOW_CONFIDENCE")
        extracted_receipts.append(receipt)

    assert len(extracted_receipts) == 16, "All 16 receipts must be extracted cleanly from replay cache"

    # 2. Parse bank CSV
    bank_lines = parse_bank_csv(bank_csv_path, run_id="run:2025-26-demo")
    assert len(bank_lines) == 16, "bank.csv must contain 16 lines (14 debits + 2 credits)"

    # 3. Execute matching
    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        date_window_days=3,
        amount_tolerance=Decimal("5.00"),
        cash_limit=Decimal("10000.00"),
    )

    matches = match(receipts=extracted_receipts, bank_lines=bank_lines, cfg=cfg)

    # 4. Verify against answer_key.json
    matched_pairs = [m for m in matches if m.kind == "MATCHED"]
    unmatched_bank = [m for m in matches if m.kind == "UNMATCHED_BANK"]
    unmatched_receipts = [m for m in matches if m.kind == "UNMATCHED_RECEIPT"]

    assert len(matched_pairs) == answer_key["summary"]["matched_pairs_count"]
    assert len(unmatched_bank) == answer_key["summary"]["unmatched_bank_debits_count"]

    # (a) Assert 13 MATCHED pairs
    assert len(matched_pairs) == 13, f"Expected 13 MATCHED pairs, got {len(matched_pairs)}"
    matched_receipt_ids = {m.receipt_id for m in matched_pairs}
    expected_matched_ids = {
        "rcpt:G01",
        "rcpt:G02",
        "rcpt:G03",
        "rcpt:G04",
        "rcpt:G05",
        "rcpt:G07",
        "rcpt:G08",
        "rcpt:G10",
        "rcpt:G11",
        "rcpt:G12",
        "rcpt:G14",
        "rcpt:G15a",
        "rcpt:G15b",
    }
    assert matched_receipt_ids == expected_matched_ids

    # (b) Assert G06 (duplicate), G09 (cash), and G13 (cash) are excluded from bank matching
    assert "rcpt:G06" not in matched_receipt_ids, "G06 exact duplicate must be excluded from bank matching"
    assert "rcpt:G09" not in matched_receipt_ids, "G09 cash receipt must be excluded from bank matching"
    assert "rcpt:G13" not in matched_receipt_ids, "G13 cash receipt must be excluded from bank matching"

    # Neither duplicate nor cash receipts should appear as UNMATCHED_RECEIPT
    unmatched_receipt_ids = {m.receipt_id for m in unmatched_receipts}
    assert "rcpt:G06" not in unmatched_receipt_ids
    assert "rcpt:G09" not in unmatched_receipt_ids
    assert "rcpt:G13" not in unmatched_receipt_ids

    # (c) Assert 1 UNMATCHED_BANK (9999.00 debit on 2026-03-05)
    assert len(unmatched_bank) == 1, f"Expected 1 UNMATCHED_BANK, got {len(unmatched_bank)}"
    unmatched_bank_line_id = unmatched_bank[0].bank_line_id
    orphan_bank_line = next(b for b in bank_lines if b.id == unmatched_bank_line_id)
    assert orphan_bank_line.txn_date == date(2026, 3, 5)
    assert orphan_bank_line.debit == Decimal("9999.00")
    assert "UNKNOWN" in orphan_bank_line.narration

    # (d) Assert G14 matches DeskCraft with amount_delta of 2.00 / -2.00 (receipt 4130.00 vs bank 4128.00)
    g14_match = next(m for m in matched_pairs if m.receipt_id == "rcpt:G14")
    assert abs(g14_match.amount_delta) == Decimal("2.00")
    assert g14_match.date_delta_days == 3

    # (e) Assert G15a and G15b are matched 1:1 to distinct bank lines
    g15a_match = next(m for m in matched_pairs if m.receipt_id == "rcpt:G15a")
    g15b_match = next(m for m in matched_pairs if m.receipt_id == "rcpt:G15b")
    assert g15a_match.bank_line_id != g15b_match.bank_line_id

    bank_15a = next(b for b in bank_lines if b.id == g15a_match.bank_line_id)
    bank_15b = next(b for b in bank_lines if b.id == g15b_match.bank_line_id)
    assert bank_15a.txn_date == date(2025, 12, 4)
    assert bank_15b.txn_date == date(2025, 12, 6)
