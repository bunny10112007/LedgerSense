from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from ledgersense.accounting.statements import profit_and_loss
from ledgersense.domain.models import (
    DeductionItem,
    DeductionSchedule,
    ITRDraft,
    JournalEntry,
    Money,
    RunConfig,
    quantize_money,
)
from ledgersense.tax.rules_engine import RuleSet, load_rules


def _get_cap_for_section(rules: RuleSet, section: str) -> Money:
    """Extract statutory deduction cap from YAML rules for section (e.g. 80C or 80D)."""
    it_rules = getattr(rules, "income_tax", rules.it)
    for d in it_rules.deductions:
        if d.id.upper() == section.upper():
            if d.cap is not None:
                return quantize_money(d.cap)
            if d.cap_self_family is not None:
                return quantize_money(d.cap_self_family)
    raise ValueError(f"Deduction section '{section}' cap not found in statutory rules")


def build_deductions(
    entries: list[JournalEntry],
    rules: RuleSet | None = None,
    cfg: RunConfig | None = None,
) -> DeductionSchedule:
    """Build Chapter VI-A Deduction Schedule from committed/eligible journal entries.

    - Filters entries to COMMITTED (or draft non-rejected entries during preview).
    - Aggregates debits for entries tagged with deduction_tag == '80C' and '80D'.
    - Retrieves statutory caps from rules YAML (never hardcoded).
    - If tax_regime_choice == 'new', allowed = 0.00, excess = claimed with explanatory note.
    - If tax_regime_choice == 'old', allowed = min(claimed, cap), excess = max(0.00, claimed - cap).
    - Always sets label='Draft schedule'.
    """
    if rules is None:
        rules = load_rules()
    if cfg is None:
        cfg = RunConfig(
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            cash_limit=Decimal("10000.00"),
            tax_regime_choice="old",
        )

    # Filter to COMMITTED entries if available, otherwise non-rejected entries
    committed = [e for e in entries if e.status == "COMMITTED"]
    target_entries = committed if committed else [e for e in entries if getattr(e, "status", "") != "REJECTED"]

    # Sum debit amounts on tagged entries
    claimed_80c = Decimal("0.00")
    claimed_80d = Decimal("0.00")

    for entry in target_entries:
        if entry.deduction_tag == "80C":
            claimed_80c += sum((line.debit for line in entry.lines), Decimal("0.00"))
        elif entry.deduction_tag == "80D":
            claimed_80d += sum((line.debit for line in entry.lines), Decimal("0.00"))

    claimed_80c = quantize_money(claimed_80c)
    claimed_80d = quantize_money(claimed_80d)

    # Caps from YAML rules
    cap_80c = _get_cap_for_section(rules, "80C")
    cap_80d = _get_cap_for_section(rules, "80D")

    # Statutory references from YAML rules
    legal_ref_80c = rules.deduction_ref("80C", cfg.regime)
    legal_ref_80d = rules.deduction_ref("80D", cfg.regime)

    if cfg.tax_regime_choice == "new":
        allowed_80c = Decimal("0.00")
        excess_80c = claimed_80c
        allowed_80d = Decimal("0.00")
        excess_80d = claimed_80d
        notes = [
            "Chapter VI-A deductions (80C, 80D) are not allowed under the New Tax Regime.",
        ]
    else:
        allowed_80c = quantize_money(min(claimed_80c, cap_80c))
        excess_80c = quantize_money(max(Decimal("0.00"), claimed_80c - cap_80c))
        allowed_80d = quantize_money(min(claimed_80d, cap_80d))
        excess_80d = quantize_money(max(Decimal("0.00"), claimed_80d - cap_80d))
        notes = [
            "Draft schedule (old regime only).",
        ]

    item_80c = DeductionItem(
        section="80C",
        legal_ref=legal_ref_80c,
        claimed=claimed_80c,
        cap=cap_80c,
        allowed=allowed_80c,
        excess=excess_80c,
    )
    item_80d = DeductionItem(
        section="80D",
        legal_ref=legal_ref_80d,
        claimed=claimed_80d,
        cap=cap_80d,
        allowed=allowed_80d,
        excess=excess_80d,
    )

    return DeductionSchedule(
        label="Draft schedule",
        regime=cfg.regime,
        tax_regime_choice=cfg.tax_regime_choice,
        items=[item_80c, item_80d],
        notes=notes,
    )


def build_itr3_draft(
    entries: list[JournalEntry],
    rules: RuleSet | None = None,
    cfg: RunConfig | None = None,
) -> ITRDraft:
    """Build draft ITR-3 payload from committed entries, P&L, and deductions."""
    if rules is None:
        rules = load_rules()
    if cfg is None:
        cfg = RunConfig(
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            cash_limit=Decimal("10000.00"),
            tax_regime_choice="old",
        )

    pnl = profit_and_loss(entries)
    deductions = build_deductions(entries, rules, cfg)

    deductions_dict = {
        item.section: {
            "section": item.section,
            "legal_ref": item.legal_ref,
            "claimed": str(item.claimed),
            "cap": str(item.cap),
            "allowed": str(item.allowed),
            "excess": str(item.excess),
        }
        for item in deductions.items
    }

    expense_breakdown = {k: str(v) for k, v in pnl.expenses.items()}
    income_breakdown = {k: str(v) for k, v in pnl.income.items()}

    financial_year = getattr(
        rules.it,
        "financial_year",
        f"{cfg.period_start.year}-{str(cfg.period_end.year)[-2:]}",
    )

    payload: dict[str, Any] = {
        "draft_watermark": "DRAFT — FOR CA / AUDITOR REVIEW ONLY",
        "financial_year": financial_year,
        "regime": cfg.regime,
        "tax_regime_choice": cfg.tax_regime_choice,
        "total_income": str(pnl.total_income),
        "total_expenses": str(pnl.total_expenses),
        "net_profit": str(pnl.net_profit),
        "expense_breakdown": expense_breakdown,
        "pnl_summary": {
            "total_income": str(pnl.total_income),
            "total_expenses": str(pnl.total_expenses),
            "net_profit": str(pnl.net_profit),
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown,
        },
        "deductions_summary": deductions_dict,
        "deductions": deductions_dict,
        "notes": deductions.notes,
    }

    return ITRDraft(
        label="Draft JSON in LedgerSense schema",
        form="ITR-3",
        regime=cfg.regime,
        field_mapping_ref="data/golden/field_mapping.csv",
        payload=payload,
    )
