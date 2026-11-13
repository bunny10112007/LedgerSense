from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ledgersense.domain.models import (
    AuditEvent,
    BankLine,
    JournalEntry,
    JournalLine,
    LineItem,
    Match,
    Receipt,
    RiskFlag,
    RunConfig,
    quantize_money,
)


def test_models_import_and_quantize():
    assert quantize_money("10.555") == Decimal("10.56")
    assert quantize_money(10.554) == Decimal("10.55")


def test_journal_entry_balanced_succeeds():
    entry = JournalEntry(
        id="je:0001",
        run_id="run:2025-26-demo",
        entry_date=date(2025, 6, 12),
        narration="Stationery purchase",
        lines=[
            JournalLine(account_code="EXPENSE_STATIONERY", debit=Decimal("10000.00"), credit=Decimal("0.00")),
            JournalLine(account_code="GST_INPUT_CGST", debit=Decimal("900.00"), credit=Decimal("0.00")),
            JournalLine(account_code="GST_INPUT_SGST", debit=Decimal("900.00"), credit=Decimal("0.00")),
            JournalLine(account_code="BANK", debit=Decimal("0.00"), credit=Decimal("11800.00")),
        ],
    )
    assert entry.id == "je:0001"
    assert len(entry.lines) == 4
    assert sum(line.debit for line in entry.lines) == Decimal("11800.00")
    assert sum(line.credit for line in entry.lines) == Decimal("11800.00")


def test_journal_entry_unbalanced_raises_validation_error():
    with pytest.raises(ValidationError, match="total debit .* != total credit"):
        JournalEntry(
            id="je:0002",
            run_id="run:2025-26-demo",
            entry_date=date(2025, 6, 12),
            narration="Unbalanced entry",
            lines=[
                JournalLine(account_code="EXPENSE_STATIONERY", debit=Decimal("10000.00"), credit=Decimal("0.00")),
                JournalLine(account_code="BANK", debit=Decimal("0.00"), credit=Decimal("9000.00")),
            ],
        )


def test_journal_entry_insufficient_lines_raises_validation_error():
    with pytest.raises(ValidationError, match="at least 2 lines"):
        JournalEntry(
            id="je:0003",
            run_id="run:2025-26-demo",
            entry_date=date(2025, 6, 12),
            narration="One line entry",
            lines=[
                JournalLine(account_code="EXPENSE", debit=Decimal("500.00"), credit=Decimal("500.00")),
            ],
        )


def test_run_config_regime_derivation():
    # Boundary: on or before 2026-03-31 => ITA_1961
    cfg_1961 = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        cash_limit=Decimal("10000.00"),
    )
    assert cfg_1961.regime == "ITA_1961"

    # From 2026-04-01 onwards => ITA_2025
    cfg_2025 = RunConfig(
        period_start=date(2026, 4, 1),
        period_end=date(2027, 3, 31),
        cash_limit=Decimal("10000.00"),
    )
    assert cfg_2025.regime == "ITA_2025"


def test_receipt_model_validation():
    receipt = Receipt(
        id="rcpt:0001",
        run_id="run:2025-26-demo",
        source_file="receipts/sample.png",
        file_hash="abc123hash",
        vendor_key="test-vendor|08AAAFA1234B1ZC",
        doc_type="gst_invoice",
        vendor_name="Test Vendor",
        vendor_gstin="08AAAFA1234B1ZC",
        invoice_date=date(2025, 5, 10),
        line_items=[
            LineItem(description="Item 1", amount=Decimal("100.00")),
        ],
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        payment_mode="bank_transfer",
    )
    assert receipt.id == "rcpt:0001"
    assert receipt.vendor_key == "test-vendor|08AAAFA1234B1ZC"


def test_audit_event_and_risk_flag_instantiation():
    flag = RiskFlag(
        id="flag:0001",
        run_id="run:2025-26-demo",
        rule_id="CASH_LIMIT",
        severity="HIGH",
        entity_ids=["rcpt:G09"],
        legal_ref="s.40A(3)",
        evidence={"amount": "12000.00", "limit": "10000.00"},
        suggested_action="Treat as disallowed",
    )
    assert flag.severity == "HIGH"
    assert flag.status == "OPEN"

    event = AuditEvent(
        id="evt:000001",
        ts=datetime.now(),
        run_id="run:2025-26-demo",
        actor="system",
        action="STATE_CHANGE",
        payload_hash="sha256hash",
    )
    assert event.actor == "system"


def test_bank_line_and_match_instantiation():
    line = BankLine(
        id="bank:0001",
        run_id="run:2025-26-demo",
        txn_date=date(2025, 6, 12),
        narration="UPI/ARAVALI",
        debit=Decimal("11800.00"),
        credit=Decimal("0.00"),
    )
    match = Match(
        id="match:0001",
        run_id="run:2025-26-demo",
        receipt_id="rcpt:G01",
        bank_line_id=line.id,
        score=0.98,
        date_delta_days=0,
        amount_delta=Decimal("0.00"),
        kind="MATCHED",
    )
    assert match.kind == "MATCHED"
    assert match.amount_delta == Decimal("0.00")
