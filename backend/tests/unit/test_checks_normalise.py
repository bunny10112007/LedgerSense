from __future__ import annotations

from decimal import Decimal

from ledgersense.domain.models import ExtractedReceipt, LineItem
from ledgersense.extraction.checks import (
    evaluate_confidence_status,
    run_arithmetic_checks,
)
from ledgersense.extraction.normalise import compute_vendor_key


def test_normalise_vendor_key() -> None:
    """Test vendor_key slugification, corporate suffix removal, and GSTIN formatting."""
    assert compute_vendor_key("Pink City Fuels", "08AAACP5678C1ZD") == "pink-city-fuels|08AAACP5678C1ZD"
    assert compute_vendor_key("DeskCraft Furniture Pvt. Ltd.", "29AAACD9012L1ZI") == "deskcraft-furniture|29AAACD9012L1ZI"
    assert compute_vendor_key("Shield Health Insurance Co. Ltd.", "27AAACS5678G1Z2") == "shield-health-insurance|27AAACS5678G1Z2"
    assert compute_vendor_key("Tech Solutions LLP", "07AABCT1234D1ZE") == "tech-solutions|07AABCT1234D1ZE"
    assert compute_vendor_key("Local tea stall", None) == "local-tea-stall|nogstin"
    assert compute_vendor_key(None, None) == "unknown|nogstin"


def test_arithmetic_checks_line_items_mismatch() -> None:
    """Arithmetic check detects line items sum mismatch with subtotal."""
    receipt = ExtractedReceipt(
        doc_type="gst_invoice",
        line_items=[
            LineItem(description="Item A", amount=Decimal("100.00")),
            LineItem(description="Item B", amount=Decimal("200.00")),
        ],
        subtotal=Decimal("350.00"),  # mismatch: 100+200 != 350
        total=Decimal("350.00"),
    )
    messages = run_arithmetic_checks(receipt)
    assert any("Line items total" in m for m in messages)


def test_arithmetic_checks_tax_total_mismatch() -> None:
    """Arithmetic check detects subtotal + taxes != total."""
    receipt = ExtractedReceipt(
        doc_type="gst_invoice",
        subtotal=Decimal("1000.00"),
        cgst=Decimal("90.00"),
        sgst=Decimal("90.00"),
        total=Decimal("1200.00"),  # mismatch: 1000+90+90 = 1180 != 1200
    )
    messages = run_arithmetic_checks(receipt)
    assert any("Subtotal" in m and "does not match total" in m for m in messages)


def test_arithmetic_checks_intra_state_cgst_sgst_mismatch() -> None:
    """Arithmetic check detects CGST != SGST for intra-state tax invoice."""
    receipt = ExtractedReceipt(
        doc_type="gst_invoice",
        subtotal=Decimal("1000.00"),
        cgst=Decimal("90.00"),
        sgst=Decimal("100.00"),  # mismatch: 90 != 100
        total=Decimal("1190.00"),
    )
    messages = run_arithmetic_checks(receipt)
    assert any("Intra-state GST mismatch" in m for m in messages)


def test_confidence_check_threshold_80() -> None:
    """Confidence check flags LOW_CONFIDENCE if any key field < 0.80."""
    receipt_ok = ExtractedReceipt(
        doc_type="gst_invoice",
        field_confidence={"vendor_gstin": 0.95, "invoice_date": 0.85, "total": 0.90},
    )
    status, warnings = evaluate_confidence_status(receipt_ok, threshold=0.80)
    assert status == "OK"
    assert len(warnings) == 0

    receipt_low = ExtractedReceipt(
        doc_type="gst_invoice",
        field_confidence={"vendor_gstin": 0.75, "invoice_date": 0.90, "total": 0.95},
    )
    status, warnings = evaluate_confidence_status(receipt_low, threshold=0.80)
    assert status == "LOW_CONFIDENCE"
    assert any("vendor_gstin" in w for w in warnings)
