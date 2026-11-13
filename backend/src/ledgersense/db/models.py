from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunRecord(SQLModel, table=True):
    __tablename__ = "runs"

    id: str = Field(primary_key=True)
    period_start: date
    period_end: date
    regime: str
    status: str = "CREATED"
    config_json: str
    created_at: datetime = Field(default_factory=utc_now)


class DocumentRecord(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    filename: str
    file_hash: str = Field(index=True)
    mime: str
    extraction_status: str = "PENDING"


class ReceiptRecord(SQLModel, table=True):
    __tablename__ = "receipts"

    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    document_id: str | None = None
    payload_json: str
    vendor_key: str = Field(index=True)


class BankLineRecord(SQLModel, table=True):
    __tablename__ = "bank_lines"

    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    txn_date: date
    narration: str
    debit: str = "0.00"
    credit: str = "0.00"
    balance: str | None = None
    ref_no: str | None = None


class MatchRecord(SQLModel, table=True):
    __tablename__ = "matches"

    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    receipt_id: str | None = Field(default=None, index=True)
    bank_line_id: str | None = Field(default=None, index=True)
    score: float = 0.0
    kind: str
    date_delta_days: int | None = None
    amount_delta: str | None = None


class RiskFlagRecord(SQLModel, table=True):
    __tablename__ = "risk_flags"

    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    rule_id: str = Field(index=True)
    severity: str
    status: str = "OPEN"
    entity_ids_json: str = "[]"
    legal_ref: str | None = None
    evidence_json: str = "{}"
    suggested_action: str = ""
    decided_by: str | None = None
    decision_reason: str | None = None
    decided_at: datetime | None = None


class JournalEntryRecord(SQLModel, table=True):
    __tablename__ = "journal_entries"

    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    entry_date: date
    status: str = "DRAFT"
    narration: str
    source_receipt_id: str | None = None
    flag_ids_json: str = "[]"
    deduction_tag: str | None = None


class JournalLineRecord(SQLModel, table=True):
    __tablename__ = "journal_lines"

    id: int | None = Field(default=None, primary_key=True)
    entry_id: str = Field(index=True)
    account_code: str
    debit: str = "0.00"
    credit: str = "0.00"


class AuditEventRecord(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: str = Field(primary_key=True)
    ts: datetime = Field(default_factory=utc_now)
    run_id: str = Field(index=True)
    actor: str
    action: str
    entity_id: str | None = None
    reason: str | None = None
    payload_hash: str


class ExtractionCacheRecord(SQLModel, table=True):
    __tablename__ = "extraction_cache"

    file_hash: str = Field(primary_key=True)
    model_id: str = Field(primary_key=True)
    prompt_version: str = Field(primary_key=True)
    response_json: str
    created_at: datetime = Field(default_factory=utc_now)


class EgressLogRecord(SQLModel, table=True):
    __tablename__ = "egress_log"

    id: str = Field(primary_key=True)
    ts: datetime = Field(default_factory=utc_now)
    run_id: str | None = Field(default=None, index=True)
    file_hash: str
    bytes: int
    model_id: str
    masked: bool = False
