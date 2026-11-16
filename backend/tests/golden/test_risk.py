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
from ledgersense.tax.risk_detectors import detect_all


def test_golden_risk_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Golden acceptance test: Execute risk detectors on 16 golden receipts and matched bank lines."""
    monkeypatch.setattr(settings, "LLM_MODE", "replay")

    golden_dir = Path(__file__).resolve().parents[3] / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    bank_csv_path = golden_dir / "bank.csv"
    answer_key_path = golden_dir / "answer_key.json"

    with open(answer_key_path, encoding="utf-8") as f:
        answer_key = json.load(f)

    # 1. Load / extract all 16 golden receipts in replay mode
    extractor = ReceiptExtractor()
    receipts = []
    for png_path in sorted(receipts_dir.glob("*.png")):
        stem = png_path.stem.lower()
        rcpt_id = f"rcpt:G{stem[1:]}" if stem.startswith("g") else f"rcpt:{stem}"
        receipt = extractor.extract_document(
            path=png_path,
            receipt_id=rcpt_id,
            source_file=f"receipts/{png_path.name}",
        )
        receipts.append(receipt)

    assert len(receipts) == 16

    # 2. Parse bank CSV
    bank_lines = parse_bank_csv(bank_csv_path, run_id="run:2025-26-demo")
    assert len(bank_lines) == 16

    # 3. Match receipts and bank lines
    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        date_window_days=3,
        amount_tolerance=Decimal("5.00"),
        cash_limit=Decimal("10000.00"),
    )
    matches = match(receipts=receipts, bank_lines=bank_lines, cfg=cfg)

    # 4. Run risk detectors
    flags = detect_all(
        receipts=receipts,
        matches=matches,
        bank_lines=bank_lines,
        cfg=cfg,
    )

    # 5. Assert summary counts
    assert len(flags) == answer_key["summary"]["total_flags_count"] == 7
    high_flags = [f for f in flags if f.severity == "HIGH"]
    medium_flags = [f for f in flags if f.severity == "MEDIUM"]
    low_flags = [f for f in flags if f.severity == "LOW"]

    assert len(high_flags) == answer_key["summary"]["high_flags_count"] == 4
    assert len(medium_flags) == answer_key["summary"]["medium_flags_count"] == 3
    assert len(low_flags) == 0

    # 6. Verify the 4 HIGH flags
    dup_flags = [f for f in high_flags if f.rule_id == "DUP_FARE"]
    assert len(dup_flags) == 1
    assert "rcpt:G06" in dup_flags[0].entity_ids
    assert dup_flags[0].evidence.get("duplicate_of") == "rcpt:G05"

    oop_flags = [f for f in high_flags if f.rule_id == "OUT_OF_PERIOD"]
    assert len(oop_flags) == 1
    assert "rcpt:G07" in oop_flags[0].entity_ids

    cash_flags = [f for f in high_flags if f.rule_id == "CASH_LIMIT"]
    assert len(cash_flags) == 1
    assert "rcpt:G09" in cash_flags[0].entity_ids

    gstin_flags = [f for f in high_flags if f.rule_id == "GSTIN_INVALID"]
    assert len(gstin_flags) == 1
    assert "rcpt:G10" in gstin_flags[0].entity_ids

    # 7. Verify the 3 MEDIUM flags
    itc_flags = [f for f in medium_flags if f.rule_id == "ITC_BLOCKED"]
    assert len(itc_flags) == 2
    itc_entity_ids = {eid for f in itc_flags for eid in f.entity_ids}
    assert itc_entity_ids == {"rcpt:G04", "rcpt:G12"}

    unmatched_bank_flags = [f for f in medium_flags if f.rule_id == "UNMATCHED_BANK"]
    assert len(unmatched_bank_flags) == 1
    # Check that the 9999.00 debit line is referenced
    orphan_bank_line = next(b for b in bank_lines if b.debit == Decimal("9999.00"))
    assert orphan_bank_line.id in unmatched_bank_flags[0].entity_ids

    # 8. Assert zero flags on G13 (petty cash 450.00 under limit)
    g13_flags = [f for f in flags if "rcpt:G13" in f.entity_ids]
    assert len(g13_flags) == 0, "G13 must have zero risk flags"

    # 9. Ensure all flags have canonical 'flag:' prefix and status OPEN
    for f in flags:
        assert f.id.startswith("flag:")
        assert f.status == "OPEN"
        assert f.legal_ref is not None
        assert f.suggested_action
        assert isinstance(f.evidence, dict)
