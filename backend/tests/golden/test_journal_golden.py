from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ledgersense.accounting.chart import (
    INPUT_CGST,
    INPUT_IGST,
    INPUT_SGST,
)
from ledgersense.accounting.journal import build_entries, commit_entries
from ledgersense.accounting.statements import profit_and_loss, trial_balance
from ledgersense.core.config import settings
from ledgersense.domain.models import RunConfig
from ledgersense.extraction.extractor import ReceiptExtractor
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.matching.matcher import match
from ledgersense.tax.risk_detectors import detect_all


def test_golden_journal_and_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    """Golden acceptance test: Reconcile receipts -> match -> flags -> journal -> commit gate -> trial balance."""
    monkeypatch.setattr(settings, "LLM_MODE", "replay")

    golden_dir = Path(__file__).resolve().parents[3] / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    bank_csv_path = golden_dir / "bank.csv"
    answer_key_path = golden_dir / "answer_key.json"

    with open(answer_key_path, encoding="utf-8") as f:
        answer_key = json.load(f)

    # 1. Extract 16 golden receipts from cache
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

    # 2. Parse bank lines
    bank_lines = parse_bank_csv(bank_csv_path, run_id="run:2025-26-demo")
    assert len(bank_lines) == 16

    # 3. Match
    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        date_window_days=3,
        amount_tolerance=Decimal("5.00"),
        cash_limit=Decimal("10000.00"),
    )
    matches = match(receipts=receipts, bank_lines=bank_lines, cfg=cfg)

    # 4. Detect Risk Flags
    flags = detect_all(
        receipts=receipts,
        matches=matches,
        bank_lines=bank_lines,
        cfg=cfg,
    )
    assert len(flags) == 7

    # 5. Build Initial Journal Entries (while all 4 HIGH flags remain OPEN)
    draft_entries = build_entries(
        receipts=receipts,
        matches=matches,
        flags=flags,
        cfg=cfg,
        bank_lines=bank_lines,
    )

    # Assert entries for G06, G07, G09, G10 are in DRAFT status
    high_rcpt_ids = {"rcpt:G06", "rcpt:G07", "rcpt:G09", "rcpt:G10"}
    for e in draft_entries:
        if e.source_receipt_id in high_rcpt_ids:
            assert e.status == "DRAFT"

    # Gate rule: commit_entries MUST block with ValueError while HIGH flags are OPEN
    with pytest.raises(ValueError, match="Gate Rule Blocked.*HIGH severity risk flags remain OPEN"):
        commit_entries(draft_entries, flags)

    # 6. Simulate Auditor Decisions on the 4 HIGH Flags
    resolved_flags = []
    for f in flags:
        if f.rule_id == "DUP_FARE":
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "REJECTED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Reject duplicate fare receipt",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        elif f.rule_id == "OUT_OF_PERIOD":
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "REJECTED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Outside financial year boundary; reject for FY25-26",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        elif f.rule_id == "CASH_LIMIT":
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Approved genuine emergency cash expense with documentation",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        elif f.rule_id == "GSTIN_INVALID":
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Approved expense booking gross; ITC denied due to bad GSTIN",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        else:
            resolved_flags.append(f)

    # 7. Rebuild entries with decisions and commit
    entries_with_decisions = build_entries(
        receipts=receipts,
        matches=matches,
        flags=resolved_flags,
        cfg=cfg,
        bank_lines=bank_lines,
    )
    committed_entries = commit_entries(entries_with_decisions, resolved_flags)

    # Exactly 14 committed entries (16 total - G06 rejected - G07 rejected = 14)
    assert len(committed_entries) == 14
    for ce in committed_entries:
        assert ce.status == "COMMITTED"

    committed_rcpt_ids = {e.source_receipt_id for e in committed_entries}
    assert "rcpt:G06" not in committed_rcpt_ids, "G06 rejected duplicate must be excluded from committed books"
    assert "rcpt:G07" not in committed_rcpt_ids, "G07 rejected out-of-period must be excluded from committed books"

    # 8. Check ITC blocked / gross expense bookings on G04, G12, and G10
    g04_entry = next(e for e in committed_entries if e.source_receipt_id == "rcpt:G04")
    g12_entry = next(e for e in committed_entries if e.source_receipt_id == "rcpt:G12")
    g10_entry = next(e for e in committed_entries if e.source_receipt_id == "rcpt:G10")

    for entry, expected_gross in [
        (g04_entry, Decimal("2100.00")),
        (g12_entry, Decimal("5900.00")),
        (g10_entry, Decimal("23600.00")),
    ]:
        assert len(entry.lines) == 2, f"Gross booked entry should have exactly 2 lines, got {len(entry.lines)}"
        debit_line = next(l for l in entry.lines if l.debit > Decimal("0.00"))
        credit_line = next(l for l in entry.lines if l.credit > Decimal("0.00"))
        assert debit_line.debit == expected_gross
        assert credit_line.credit == expected_gross
        # Zero Input GST
        gst_lines = [l for l in entry.lines if l.account_code in (INPUT_CGST, INPUT_SGST, INPUT_IGST)]
        assert len(gst_lines) == 0

    # 9. Verify Deduction Tagging on G08 and G11
    g08_entry = next(e for e in committed_entries if e.source_receipt_id == "rcpt:G08")
    assert g08_entry.deduction_tag == "80D"
    assert sum(l.debit for l in g08_entry.lines) == Decimal(answer_key["deductions"]["80D_if_g07_rejected"]["claimed"])

    g11_entry = next(e for e in committed_entries if e.source_receipt_id == "rcpt:G11")
    assert g11_entry.deduction_tag == "80C"
    assert sum(l.debit for l in g11_entry.lines) == Decimal(answer_key["deductions"]["80C"]["claimed"])

    # 10. Compute and verify Trial Balance
    tb = trial_balance(committed_entries)
    assert tb.balanced is True
    assert tb.total_debit == tb.total_credit == Decimal("131880.00")

    # Verify PnL
    pnl = profit_and_loss(committed_entries)
    assert pnl.total_income == Decimal("0.00")
    assert pnl.total_expenses == Decimal("126359.52")
    assert pnl.net_profit == -Decimal("126359.52")
