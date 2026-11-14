from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from ledgersense.domain.models import Money, Regime, Severity, quantize_money

RULES_DIR = Path(__file__).resolve().parent / "rules"


def derive_regime(period_end: date) -> Regime:
    """Derive regime from period_end: ITA_1961 on or before 2026-03-31, ITA_2025 thereafter."""
    if period_end <= date(2026, 3, 31):
        return "ITA_1961"
    return "ITA_2025"


def resolve_legal_ref(
    ref_1961: str | None,
    ref_2025: str | None,
    regime: Regime,
) -> str:
    """Return the active regime's statutory reference, or 'mapping pending' if None."""
    target_ref = ref_1961 if regime == "ITA_1961" else ref_2025
    if target_ref is not None and str(target_ref).strip():
        return str(target_ref).strip()
    return "mapping pending"


# --- Pydantic Schemas for YAML Rules ---


class BlockedItcCategoryRule(BaseModel):
    id: str
    ref: str
    keywords: list[str] = Field(default_factory=list)
    action: Literal["BLOCK_ITC", "BLOCK_ITC_NEEDS_CONFIRMATION"]
    severity: Severity = "MEDIUM"


class GstBlockedItcRules(BaseModel):
    version: int
    verified_by: str | None = None
    categories: list[BlockedItcCategoryRule] = Field(default_factory=list)


class CashExpenseLimitRule(BaseModel):
    amount: Money
    ref_1961: str = "s.40A(3)"
    ref_2025: str | None = None
    severity: Severity = "HIGH"

    @field_validator("amount", mode="before")
    @classmethod
    def quantize_amount(cls, v: Any) -> Money:
        return quantize_money(v)


class DeductionRuleItem(BaseModel):
    id: str  # e.g. "80C", "80D"
    cap: Money | None = None
    cap_self_family: Money | None = None
    ref_1961: str
    ref_2025: str | None = None
    old_regime_only: bool = True

    @field_validator("cap", "cap_self_family", mode="before")
    @classmethod
    def quantize_caps(cls, v: Any) -> Money | None:
        if v is not None:
            return quantize_money(v)
        return None


class IncomeTaxRules(BaseModel):
    version: int
    financial_year: str
    regime: Regime = "ITA_1961"
    verified_by: str | None = None
    cash_expense_limit: CashExpenseLimitRule
    deductions: list[DeductionRuleItem] = Field(default_factory=list)


class RuleSet(BaseModel):
    """Container holding loaded GST and Income Tax statutory rules."""

    gst: GstBlockedItcRules
    it: IncomeTaxRules

    @property
    def is_gst_verified(self) -> bool:
        return self.gst.verified_by is not None

    @property
    def is_it_verified(self) -> bool:
        return self.it.verified_by is not None

    def cash_limit_ref(self, regime: Regime) -> str:
        """Resolve statutory reference for cash expense limit under the given regime."""
        return resolve_legal_ref(
            self.it.cash_expense_limit.ref_1961,
            self.it.cash_expense_limit.ref_2025,
            regime,
        )

    def deduction_ref(self, section: str, regime: Regime) -> str:
        """Resolve statutory reference for a specific deduction section under the given regime."""
        for item in self.it.deductions:
            if item.id.lower() == section.lower():
                return resolve_legal_ref(item.ref_1961, item.ref_2025, regime)
        raise ValueError(f"Deduction section '{section}' not found in IT rules")

    def resolve_legal_ref(
        self,
        ref_1961: str | None,
        ref_2025: str | None,
        regime: Regime,
    ) -> str:
        return resolve_legal_ref(ref_1961, ref_2025, regime)


def load_gst_rules(path: Path | str | None = None) -> GstBlockedItcRules:
    """Load and validate gst_blocked_itc.yaml."""
    file_path = Path(path) if path else (RULES_DIR / "gst_blocked_itc.yaml")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return GstBlockedItcRules.model_validate(data)


def load_it_rules(path: Path | str | None = None) -> IncomeTaxRules:
    """Load and validate it_fy2025_26.yaml."""
    file_path = Path(path) if path else (RULES_DIR / "it_fy2025_26.yaml")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return IncomeTaxRules.model_validate(data)


def load_rules(rules_dir: Path | str | None = None) -> RuleSet:
    """Load all statutory rule YAML files from rules_dir (default: tax/rules/)."""
    target_dir = Path(rules_dir) if rules_dir else RULES_DIR
    gst_rules = load_gst_rules(target_dir / "gst_blocked_itc.yaml")
    it_rules = load_it_rules(target_dir / "it_fy2025_26.yaml")
    return RuleSet(gst=gst_rules, it=it_rules)
