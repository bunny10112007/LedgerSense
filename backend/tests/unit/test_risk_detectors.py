from __future__ import annotations

from datetime import date
from decimal import Decimal

from ledgersense.domain.models import Match, Receipt, RunConfig
from ledgersense.tax.risk_detectors import (
    detect_all,
    detect_arithmetic_mismatches,
    detect_cash_limit,
    detect_duplicates,
    detect_low_confidence,
    detect_unmatched_receipts,
)
from ledgersense.tax.rules_engine import load_rules


def test_dup_doc_non_fare_medium_severity() -> None:
    """Non-fare duplicates (e.g. gst_invoice or receipt) emit DUP_DOC with MEDIUM severity."""
    r1 = Receipt(
        id="rcpt:1001",
        run_id="run:demo",
        source_file="f1.png",
        file_hash="hash1",
        vendor_key="tech-corp|27AAPFU0939F1ZV",
        doc_type="gst_invoice",
        vendor_name="Tech Corp",
        vendor_gstin="27AAPFU0939F1ZV",
        invoice_no="INV-99",
        invoice_date=date(2025, 6, 1),
        total=Decimal("5000.00"),
    )
    r2 = Receipt(
        id="rcpt:1002",
        run_id="run:demo",
        source_file="f2.png",
        file_hash="hash2",
        vendor_key="tech-corp|27AAPFU0939F1ZV",
        doc_type="gst_invoice",
        vendor_name="Tech Corp",
        vendor_gstin="27AAPFU0939F1ZV",
        invoice_no="INV-99",
        invoice_date=date(2025, 6, 1),
        total=Decimal("5000.00"),
    )

    flags = detect_duplicates([r1, r2], run_id="run:demo")
    assert len(flags) == 1
    assert flags[0].rule_id == "DUP_DOC"
    assert flags[0].severity == "MEDIUM"
    assert "rcpt:1002" in flags[0].entity_ids
    assert flags[0].evidence["duplicate_of"] == "rcpt:1001"


def test_dup_doc_near_duplicate_missing_invoice_no() -> None:
    """Near duplicate: same vendor_key, total, date within 1 day, missing invoice_no."""
    r1 = Receipt(
        id="rcpt:2001",
        run_id="run:demo",
        source_file="f1.png",
        file_hash="hash1",
        vendor_key="uber-india|nogstin",
        doc_type="fare",
        vendor_name="Uber India",
        invoice_no=None,
        invoice_date=date(2025, 8, 10),
        total=Decimal("350.00"),
    )
    r2 = Receipt(
        id="rcpt:2002",
        run_id="run:demo",
        source_file="f2.png",
        file_hash="hash2",
        vendor_key="uber-india|nogstin",
        doc_type="fare",
        vendor_name="Uber India",
        invoice_no=None,
        invoice_date=date(2025, 8, 11),  # 1 day delta
        total=Decimal("350.00"),
    )

    flags = detect_duplicates([r1, r2], run_id="run:demo")
    assert len(flags) == 1
    assert flags[0].rule_id == "DUP_FARE"
    assert flags[0].severity == "HIGH"
    assert "rcpt:2002" in flags[0].entity_ids
    assert flags[0].evidence["kind"] == "near"


def test_unmatched_receipt_detector() -> None:
    """UNMATCHED_RECEIPT match produces a RiskFlag."""
    m = Match(
        id="match:rcpt:0001",
        run_id="run:demo",
        receipt_id="rcpt:0001",
        bank_line_id=None,
        score=0.0,
        kind="UNMATCHED_RECEIPT",
    )
    flags = detect_unmatched_receipts([m], run_id="run:demo")
    assert len(flags) == 1
    assert flags[0].rule_id == "UNMATCHED_RECEIPT"
    assert flags[0].severity == "MEDIUM"
    assert flags[0].entity_ids == ["rcpt:0001"]


def test_arithmetic_mismatch_detector() -> None:
    """Receipt with check_messages triggers ARITH_MISMATCH."""
    r = Receipt(
        id="rcpt:3001",
        run_id="run:demo",
        source_file="f.png",
        file_hash="h",
        vendor_key="vendor|nogstin",
        doc_type="receipt",
        check_messages=["Subtotal 100 + CGST 9 + SGST 9 != Total 150"],
        total=Decimal("150.00"),
    )
    flags = detect_arithmetic_mismatches([r], run_id="run:demo")
    assert len(flags) == 1
    assert flags[0].rule_id == "ARITH_MISMATCH"
    assert flags[0].severity == "MEDIUM"
    assert flags[0].entity_ids == ["rcpt:3001"]


def test_low_confidence_detector() -> None:
    """Receipt with extraction_status LOW_CONFIDENCE triggers LOW_CONFIDENCE flag."""
    r = Receipt(
        id="rcpt:4001",
        run_id="run:demo",
        source_file="f.png",
        file_hash="h",
        vendor_key="vendor|nogstin",
        doc_type="receipt",
        extraction_status="LOW_CONFIDENCE",
        field_confidence={"total": 0.55},
        total=Decimal("100.00"),
    )
    flags = detect_low_confidence([r], run_id="run:demo")
    assert len(flags) == 1
    assert flags[0].rule_id == "LOW_CONFIDENCE"
    assert flags[0].severity == "LOW"
    assert flags[0].entity_ids == ["rcpt:4001"]


def test_cash_limit_under_ita_2025_resolves_mapping_pending() -> None:
    """CASH_LIMIT detector resolves legal_ref to 'mapping pending' under ITA_2025."""
    r = Receipt(
        id="rcpt:5001",
        run_id="run:2026-27",
        source_file="f.png",
        file_hash="h",
        vendor_key="vendor|nogstin",
        doc_type="receipt",
        payment_mode="cash",
        invoice_date=date(2026, 5, 10),
        total=Decimal("15000.00"),
    )
    cfg_2025 = RunConfig(
        period_start=date(2026, 4, 1),
        period_end=date(2027, 3, 31),
        cash_limit=Decimal("10000.00"),
    )
    rules = load_rules()

    flags = detect_cash_limit([r], cfg=cfg_2025, rules=rules, run_id="run:2026-27")
    assert len(flags) == 1
    assert flags[0].rule_id == "CASH_LIMIT"
    assert flags[0].severity == "HIGH"
    assert flags[0].legal_ref == "mapping pending"


def test_detect_all_empty_inputs() -> None:
    """detect_all handles empty inputs gracefully."""
    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        cash_limit=Decimal("10000.00"),
    )
    flags = detect_all(receipts=[], matches=[], bank_lines=[], cfg=cfg)
    assert flags == []
