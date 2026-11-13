from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

# Money is Decimal, serialised as str; quantize to 0.01 with ROUND_HALF_UP at boundaries
Money = Decimal


def quantize_money(amount: Decimal | str | float) -> Money:
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


DocType = Literal[
    "gst_invoice",
    "receipt",
    "fuel_slip",
    "dining_bill",
    "fare",
    "premium_receipt",
    "other",
]

PayMode = Literal["cash", "upi", "card", "bank_transfer", "unknown"]

Severity = Literal["LOW", "MEDIUM", "HIGH"]

FlagStatus = Literal["OPEN", "APPROVED", "REJECTED", "AUTO_RESOLVED"]

Regime = Literal["ITA_1961", "ITA_2025"]

RunStatus = Literal[
    "CREATED",
    "EXTRACTED",
    "VALIDATED",
    "MATCHED",
    "RISK_DONE",
    "AWAITING_REVIEW",
    "APPROVED",
    "COMMITTED",
    "FAILED",
]

ID_PREFIXES: dict[str, str] = {
    "run": "run:",
    "receipt": "rcpt:",
    "bank": "bank:",
    "match": "match:",
    "flag": "flag:",
    "journal": "je:",
    "event": "evt:",
}

# Valid state machine transitions per Blueprint Section 4
ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    "CREATED": {"EXTRACTED", "FAILED"},
    "EXTRACTED": {"VALIDATED", "FAILED"},
    "VALIDATED": {"MATCHED", "FAILED"},
    "MATCHED": {"RISK_DONE", "FAILED"},
    "RISK_DONE": {"AWAITING_REVIEW", "APPROVED", "FAILED"},
    "AWAITING_REVIEW": {"RISK_DONE", "APPROVED", "FAILED"},
    "APPROVED": {"COMMITTED", "FAILED"},
    "COMMITTED": set(),  # Terminal state
    "FAILED": set(),  # Terminal state
}


class LineItem(BaseModel):
    description: str
    quantity: Decimal | None = None
    unit_price: Money | None = None
    amount: Money
    hsn_sac: str | None = None
    tax_rate_pct: Decimal | None = None


class ExtractedReceipt(BaseModel):
    """What the LLM layer may produce."""

    doc_type: DocType
    vendor_name: str | None = None
    vendor_gstin: str | None = None  # copied verbatim, never inferred
    invoice_no: str | None = None
    invoice_date: date | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Money | None = None
    cgst: Money = Decimal("0.00")
    sgst: Money = Decimal("0.00")
    igst: Money = Decimal("0.00")
    total: Money | None = None
    payment_mode: PayMode = "unknown"
    field_confidence: dict[str, float] = Field(
        default_factory=dict
    )  # keys: vendor_gstin, invoice_date, total


class Receipt(ExtractedReceipt):
    """Persisted record."""

    id: str  # e.g. "rcpt:0001"
    run_id: str
    source_file: str
    file_hash: str
    vendor_key: str  # normalised name + gstin, see 6.1
    extraction_status: Literal["OK", "LOW_CONFIDENCE", "FAILED"] = "OK"
    check_messages: list[str] = Field(
        default_factory=list
    )  # arithmetic / format check results


class BankLine(BaseModel):
    id: str  # e.g. "bank:0001"
    run_id: str
    txn_date: date
    narration: str
    debit: Money = Decimal("0.00")
    credit: Money = Decimal("0.00")
    balance: Money | None = None
    ref_no: str | None = None


class Match(BaseModel):
    id: str
    run_id: str
    receipt_id: str | None = None  # None => orphan bank line
    bank_line_id: str | None = None  # None => unmatched receipt
    score: float = 0.0
    date_delta_days: int | None = None
    amount_delta: Money | None = None
    kind: Literal["MATCHED", "UNMATCHED_RECEIPT", "UNMATCHED_BANK", "AMBIGUOUS"]


class RiskFlag(BaseModel):
    id: str
    run_id: str
    rule_id: str  # e.g. "CASH_LIMIT", "DUP_FARE"
    severity: Severity
    entity_ids: list[str] = Field(
        default_factory=list
    )  # receipt / bank / entry ids involved
    legal_ref: str | None = None  # resolved per regime
    evidence: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str
    status: FlagStatus = "OPEN"
    decided_by: str | None = None
    decision_reason: str | None = None
    decided_at: datetime | None = None


class JournalLine(BaseModel):
    account_code: str
    debit: Money = Decimal("0.00")
    credit: Money = Decimal("0.00")


class JournalEntry(BaseModel):
    id: str
    run_id: str
    entry_date: date
    narration: str
    lines: list[JournalLine] = Field(default_factory=list)
    status: Literal["DRAFT", "COMMITTED"] = "DRAFT"
    source_receipt_id: str | None = None
    flag_ids: list[str] = Field(default_factory=list)
    deduction_tag: Literal["80C", "80D"] | None = None

    @model_validator(mode="after")
    def validate_lines(self) -> JournalEntry:
        if len(self.lines) < 2:
            raise ValueError("JournalEntry must have at least 2 lines")
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)
        if total_debit != total_credit:
            raise ValueError(
                f"Unbalanced JournalEntry: total debit ({total_debit}) != total credit ({total_credit})"
            )
        return self


class AuditEvent(BaseModel):
    """Append-only audit event."""

    id: str
    ts: datetime
    run_id: str
    actor: str  # "system" | "auditor-a" | "auditor-b"
    action: str  # "STATE_CHANGE", "FLAG_APPROVED", "LLM_CALL", ...
    entity_id: str | None = None
    reason: str | None = None
    payload_hash: str


class RunConfig(BaseModel):
    period_start: date
    period_end: date
    date_window_days: int = 3
    amount_tolerance: Money = Decimal("5.00")
    cash_limit: Money  # from rules YAML, not typed by hand
    tax_regime_choice: Literal["old", "new"] = "old"  # 80C/80D only if "old"

    @computed_field
    @property
    def regime(self) -> Regime:
        """Derive regime from the run period: ITA_1961 for periods ending on or before 31 Mar 2026, ITA_2025 from 1 Apr 2026."""
        if self.period_end <= date(2026, 3, 31):
            return "ITA_1961"
        return "ITA_2025"


class Run(BaseModel):
    """Reconciliation run entity matching Blueprint Section 4 & 5."""

    id: str  # e.g. "run:2025-26-demo"
    period_start: date
    period_end: date
    regime: Regime
    status: RunStatus = "CREATED"
    config: RunConfig
    created_at: datetime = Field(default_factory=datetime.now)


# --- Section 9 Inter-Module Pure Function Return Models ---


class GstinResult(BaseModel):
    """Return type of tax.gstin.validate_gstin."""

    ok: bool
    reason: str | None = None
    expected_check_char: str | None = None


class TrialBalanceRow(BaseModel):
    account_code: str
    debit: Money = Decimal("0.00")
    credit: Money = Decimal("0.00")


class TrialBalance(BaseModel):
    """Return type of accounting.statements.trial_balance."""

    accounts: list[TrialBalanceRow] = Field(default_factory=list)
    total_debit: Money = Decimal("0.00")
    total_credit: Money = Decimal("0.00")
    balanced: bool = True


class PnL(BaseModel):
    """Return type of accounting.statements.profit_and_loss."""

    income: dict[str, Money] = Field(default_factory=dict)
    expenses: dict[str, Money] = Field(default_factory=dict)
    total_income: Money = Decimal("0.00")
    total_expenses: Money = Decimal("0.00")
    net_profit: Money = Decimal("0.00")


class DeductionItem(BaseModel):
    section: Literal["80C", "80D"]
    legal_ref: str
    claimed: Money
    cap: Money
    allowed: Money
    excess: Money


class DeductionSchedule(BaseModel):
    """Return type of tax.itr_mapper.build_deductions."""

    label: str = "Draft schedule"
    regime: Regime
    tax_regime_choice: Literal["old", "new"]
    items: list[DeductionItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ITRDraft(BaseModel):
    """Return type of tax.itr_mapper.build_itr3_draft."""

    label: str = "Draft JSON in LedgerSense schema"
    form: str = "ITR-3"
    regime: Regime
    payload: dict[str, Any] = Field(default_factory=dict)
    field_mapping_ref: str = "field_mapping.csv"
