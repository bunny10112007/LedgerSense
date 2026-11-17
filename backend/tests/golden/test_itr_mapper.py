from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ledgersense.accounting.journal import build_entries, commit_entries
from ledgersense.core.config import settings
from ledgersense.domain.models import RunConfig
from ledgersense.extraction.extractor import ReceiptExtractor
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.matching.matcher import match
from ledgersense.tax.itr_mapper import build_deductions, build_itr3_draft
from ledgersense.tax.risk_detectors import detect_all
from ledgersense.tax.rules_engine import load_rules


@pytest.fixture
def golden_setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_MODE", "replay")

    golden_dir = Path(__file__).resolve().parents[3] / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    bank_csv_path = golden_dir / "bank.csv"

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

    bank_lines = parse_bank_csv(bank_csv_path, run_id="run:2025-26-demo")

    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        date_window_days=3,
        amount_tolerance=Decimal("5.00"),
        cash_limit=Decimal("10000.00"),
        tax_regime_choice="old",
    )

    matches = match(receipts=receipts, bank_lines=bank_lines, cfg=cfg)
    flags = detect_all(
        receipts=receipts,
        matches=matches,
        bank_lines=bank_lines,
        cfg=cfg,
    )
    rules = load_rules()

    return {
        "receipts": receipts,
        "bank_lines": bank_lines,
        "cfg": cfg,
        "matches": matches,
        "flags": flags,
        "rules": rules,
        "golden_dir": golden_dir,
    }


def test_field_mapping_csv(golden_setup):
    """Verify data/golden/field_mapping.csv structure and required schedules."""
    csv_path = golden_setup["golden_dir"] / "field_mapping.csv"
    assert csv_path.exists(), f"Missing field mapping CSV at {csv_path}"

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 10
    headers = reader.fieldnames or []
    assert "internal_field" in headers
    assert "itr3_schedule" in headers
    assert "itr3_field_name" in headers
    assert "json_path" in headers

    schedules = {r["itr3_schedule"] for r in rows}
    assert "Schedule PL" in schedules
    assert "Schedule BP" in schedules
    assert "Schedule VI-A" in schedules

    # Verify both verified and TBD paths exist
    json_paths = [r["json_path"] for r in rows]
    assert any("TBD (Draft Schema)" in p for p in json_paths)
    assert any("ITR.ITR3" in p for p in json_paths)


def test_case_1_standard_golden_run_deductions(golden_setup):
    """Test Case 1: Standard Golden Run (G07 rejected, G08 & G11 committed, old regime)."""
    receipts = golden_setup["receipts"]
    matches = golden_setup["matches"]
    flags = golden_setup["flags"]
    cfg = golden_setup["cfg"]
    rules = golden_setup["rules"]
    bank_lines = golden_setup["bank_lines"]

    # Resolve HIGH flags (reject G06 & G07, approve G09 & G10)
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
        elif f.rule_id in ("CASH_LIMIT", "GSTIN_INVALID"):
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Auditor approved after audit verification",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        else:
            resolved_flags.append(f)

    draft_entries = build_entries(receipts, matches, resolved_flags, cfg, bank_lines)
    committed_entries = commit_entries(draft_entries, resolved_flags)
    assert len(committed_entries) == 14

    schedule = build_deductions(committed_entries, rules, cfg)
    assert schedule.label == "Draft schedule"
    assert schedule.regime == "ITA_1961"
    assert schedule.tax_regime_choice == "old"

    item_80c = next(i for i in schedule.items if i.section == "80C")
    item_80d = next(i for i in schedule.items if i.section == "80D")

    # Assert 80C
    assert item_80c.claimed == Decimal("30000.00")
    assert item_80c.cap == Decimal("150000.00")
    assert item_80c.allowed == Decimal("30000.00")
    assert item_80c.excess == Decimal("0.00")
    assert item_80c.legal_ref == "s.80C"

    # Assert 80D
    assert item_80d.claimed == Decimal("18000.00")
    assert item_80d.cap == Decimal("25000.00")
    assert item_80d.allowed == Decimal("18000.00")
    assert item_80d.excess == Decimal("0.00")
    assert item_80d.legal_ref == "s.80D"


def test_case_2_g07_approved_deductions(golden_setup):
    """Test Case 2: G07 ₹24,000.00 approved into period alongside G08 ₹18,000.00."""
    receipts = golden_setup["receipts"]
    matches = golden_setup["matches"]
    flags = golden_setup["flags"]
    cfg = golden_setup["cfg"]
    rules = golden_setup["rules"]
    bank_lines = golden_setup["bank_lines"]

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
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Auditor approved health premium receipt into period",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        elif f.rule_id in ("CASH_LIMIT", "GSTIN_INVALID"):
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Auditor approved after audit verification",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        else:
            resolved_flags.append(f)

    draft_entries = build_entries(receipts, matches, resolved_flags, cfg, bank_lines)
    committed_entries = commit_entries(draft_entries, resolved_flags)
    assert len(committed_entries) == 15  # G06 rejected, G07 approved

    schedule = build_deductions(committed_entries, rules, cfg)
    item_80d = next(i for i in schedule.items if i.section == "80D")

    # Assert 80D with combined G07 (24000.00) + G08 (18000.00) = 42000.00
    assert item_80d.claimed == Decimal("42000.00")
    assert item_80d.cap == Decimal("25000.00")
    assert item_80d.allowed == Decimal("25000.00")
    assert item_80d.excess == Decimal("17000.00")


def test_case_3_new_tax_regime(golden_setup):
    """Test Case 3: tax_regime_choice == 'new' disallows Chapter VI-A deductions."""
    receipts = golden_setup["receipts"]
    matches = golden_setup["matches"]
    flags = golden_setup["flags"]
    cfg = golden_setup["cfg"]
    rules = golden_setup["rules"]
    bank_lines = golden_setup["bank_lines"]

    resolved_flags = []
    for f in flags:
        if f.rule_id in ("DUP_FARE", "OUT_OF_PERIOD"):
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "REJECTED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Reject flag",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        elif f.rule_id in ("CASH_LIMIT", "GSTIN_INVALID"):
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Approve flag",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        else:
            resolved_flags.append(f)

    draft_entries = build_entries(receipts, matches, resolved_flags, cfg, bank_lines)
    committed_entries = commit_entries(draft_entries, resolved_flags)

    cfg_new = cfg.model_copy(update={"tax_regime_choice": "new"})
    schedule = build_deductions(committed_entries, rules, cfg_new)

    assert schedule.tax_regime_choice == "new"
    assert any("not allowed under the New Tax Regime" in n for n in schedule.notes)

    for item in schedule.items:
        assert item.allowed == Decimal("0.00")
        assert item.excess == item.claimed

    item_80c = next(i for i in schedule.items if i.section == "80C")
    item_80d = next(i for i in schedule.items if i.section == "80D")
    assert item_80c.claimed == Decimal("30000.00")
    assert item_80c.allowed == Decimal("0.00")
    assert item_80c.excess == Decimal("30000.00")

    assert item_80d.claimed == Decimal("18000.00")
    assert item_80d.allowed == Decimal("0.00")
    assert item_80d.excess == Decimal("18000.00")


def test_case_4_build_itr3_draft(golden_setup):
    """Test Case 4: build_itr3_draft generates draft JSON payload matching golden P&L."""
    receipts = golden_setup["receipts"]
    matches = golden_setup["matches"]
    flags = golden_setup["flags"]
    cfg = golden_setup["cfg"]
    rules = golden_setup["rules"]
    bank_lines = golden_setup["bank_lines"]

    resolved_flags = []
    for f in flags:
        if f.rule_id in ("DUP_FARE", "OUT_OF_PERIOD"):
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "REJECTED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Reject flag",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        elif f.rule_id in ("CASH_LIMIT", "GSTIN_INVALID"):
            resolved_flags.append(
                f.model_copy(
                    update={
                        "status": "APPROVED",
                        "decided_by": "auditor-a",
                        "decision_reason": "Approve flag",
                        "decided_at": date(2026, 3, 31),
                    }
                )
            )
        else:
            resolved_flags.append(f)

    draft_entries = build_entries(receipts, matches, resolved_flags, cfg, bank_lines)
    committed_entries = commit_entries(draft_entries, resolved_flags)

    itr = build_itr3_draft(committed_entries, rules, cfg)

    assert itr.label == "Draft JSON in LedgerSense schema"
    assert itr.form == "ITR-3"
    assert itr.regime == "ITA_1961"
    assert itr.field_mapping_ref == "data/golden/field_mapping.csv"

    payload = itr.payload
    assert payload["total_expenses"] == "126359.52"
    assert payload["total_income"] == "0.00"
    assert payload["net_profit"] == "-126359.52"
    assert payload["draft_watermark"] == "DRAFT — FOR CA / AUDITOR REVIEW ONLY"
    assert payload["financial_year"] == "2025-26"

    # Deduction summary in payload
    assert payload["deductions"]["80C"]["claimed"] == "30000.00"
    assert payload["deductions"]["80C"]["allowed"] == "30000.00"
    assert payload["deductions"]["80D"]["claimed"] == "18000.00"
    assert payload["deductions"]["80D"]["allowed"] == "18000.00"


def test_statutory_refs_ita_2025():
    """Verify statutory legal reference mapping under ITA_2025 (s.123 and s.126)."""
    rules = load_rules()
    cfg_2025 = RunConfig(
        period_start=date(2026, 4, 1),
        period_end=date(2027, 3, 31),
        cash_limit=Decimal("10000.00"),
        tax_regime_choice="old",
    )
    assert cfg_2025.regime == "ITA_2025"
    assert rules.deduction_ref("80C", cfg_2025.regime) == "s.123"
    assert rules.deduction_ref("80D", cfg_2025.regime) == "s.126"
