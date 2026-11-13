import json
from datetime import UTC, datetime

from sqlmodel import Session, select


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt

from ledgersense.db.models import (
    AuditEventRecord,
    BankLineRecord,
    DocumentRecord,
    EgressLogRecord,
    ExtractionCacheRecord,
    JournalEntryRecord,
    JournalLineRecord,
    MatchRecord,
    ReceiptRecord,
    RiskFlagRecord,
    RunRecord,
)
from ledgersense.domain.models import (
    AuditEvent,
    BankLine,
    JournalEntry,
    Match,
    Receipt,
    RiskFlag,
    Run,
)


class Repository:
    """Data repository providing typed operations over SQLModel tables."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Run ---
    def create_run(self, run: Run) -> RunRecord:
        record = RunRecord(
            id=run.id,
            period_start=run.period_start,
            period_end=run.period_end,
            regime=run.regime,
            status=run.status,
            config_json=run.config.model_dump_json(),
            created_at=ensure_utc(run.created_at) or datetime.now(UTC),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.session.get(RunRecord, run_id)

    def update_run_status(self, run_id: str, status: str) -> RunRecord | None:
        run = self.get_run(run_id)
        if run:
            run.status = status
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
        return run

    # --- Documents ---
    def save_documents(self, documents: list[DocumentRecord]) -> None:
        for doc in documents:
            self.session.add(doc)
        self.session.commit()

    def get_documents(self, run_id: str) -> list[DocumentRecord]:
        statement = select(DocumentRecord).where(DocumentRecord.run_id == run_id)
        return list(self.session.exec(statement).all())

    # --- Receipts ---
    def save_receipts(self, receipts: list[Receipt]) -> None:
        for r in receipts:
            record = ReceiptRecord(
                id=r.id,
                run_id=r.run_id,
                document_id=r.source_file,
                payload_json=r.model_dump_json(),
                vendor_key=r.vendor_key,
            )
            self.session.add(record)
        self.session.commit()

    def get_receipts(self, run_id: str) -> list[ReceiptRecord]:
        statement = select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)
        return list(self.session.exec(statement).all())

    # --- Bank Lines ---
    def save_bank_lines(self, lines: list[BankLine]) -> None:
        for b in lines:
            record = BankLineRecord(
                id=b.id,
                run_id=b.run_id,
                txn_date=b.txn_date,
                narration=b.narration,
                debit=str(b.debit),
                credit=str(b.credit),
                balance=str(b.balance) if b.balance is not None else None,
                ref_no=b.ref_no,
            )
            self.session.add(record)
        self.session.commit()

    def get_bank_lines(self, run_id: str) -> list[BankLineRecord]:
        statement = select(BankLineRecord).where(BankLineRecord.run_id == run_id)
        return list(self.session.exec(statement).all())

    # --- Matches ---
    def save_matches(self, matches: list[Match]) -> None:
        for m in matches:
            record = MatchRecord(
                id=m.id,
                run_id=m.run_id,
                receipt_id=m.receipt_id,
                bank_line_id=m.bank_line_id,
                score=m.score,
                kind=m.kind,
                date_delta_days=m.date_delta_days,
                amount_delta=str(m.amount_delta) if m.amount_delta is not None else None,
            )
            self.session.add(record)
        self.session.commit()

    def get_matches(self, run_id: str) -> list[MatchRecord]:
        statement = select(MatchRecord).where(MatchRecord.run_id == run_id)
        return list(self.session.exec(statement).all())

    # --- Risk Flags ---
    def save_risk_flags(self, flags: list[RiskFlag]) -> None:
        for f in flags:
            record = RiskFlagRecord(
                id=f.id,
                run_id=f.run_id,
                rule_id=f.rule_id,
                severity=f.severity,
                status=f.status,
                entity_ids_json=json.dumps(f.entity_ids),
                legal_ref=f.legal_ref,
                evidence_json=json.dumps(f.evidence),
                suggested_action=f.suggested_action,
                decided_by=f.decided_by,
                decision_reason=f.decision_reason,
                decided_at=f.decided_at,
            )
            self.session.add(record)
        self.session.commit()

    def get_risk_flags(self, run_id: str, status: str | None = None) -> list[RiskFlagRecord]:
        statement = select(RiskFlagRecord).where(RiskFlagRecord.run_id == run_id)
        if status:
            statement = statement.where(RiskFlagRecord.status == status)
        return list(self.session.exec(statement).all())

    def update_risk_flag_decision(
        self, flag_id: str, decided_by: str, decision: str, reason: str
    ) -> RiskFlagRecord | None:
        flag = self.session.get(RiskFlagRecord, flag_id)
        if flag:
            flag.status = "APPROVED" if decision.lower() == "approve" else "REJECTED"
            flag.decided_by = decided_by
            flag.decision_reason = reason
            flag.decided_at = datetime.now(UTC)
            self.session.add(flag)
            self.session.commit()
            self.session.refresh(flag)
        return flag

    # --- Journal Entries & Lines ---
    def save_journal_entries(self, entries: list[JournalEntry]) -> None:
        for entry in entries:
            entry_record = JournalEntryRecord(
                id=entry.id,
                run_id=entry.run_id,
                entry_date=entry.entry_date,
                status=entry.status,
                narration=entry.narration,
                source_receipt_id=entry.source_receipt_id,
                flag_ids_json=json.dumps(entry.flag_ids),
                deduction_tag=entry.deduction_tag,
            )
            self.session.add(entry_record)
            for line in entry.lines:
                line_record = JournalLineRecord(
                    entry_id=entry.id,
                    account_code=line.account_code,
                    debit=str(line.debit),
                    credit=str(line.credit),
                )
                self.session.add(line_record)
        self.session.commit()

    def get_journal_entries(
        self, run_id: str, status: str | None = None
    ) -> list[JournalEntryRecord]:
        statement = select(JournalEntryRecord).where(JournalEntryRecord.run_id == run_id)
        if status:
            statement = statement.where(JournalEntryRecord.status == status)
        return list(self.session.exec(statement).all())

    # --- Audit Events (Append-only) ---
    def append_audit_event(self, event: AuditEvent) -> AuditEventRecord:
        record = AuditEventRecord(
            id=event.id,
            ts=ensure_utc(event.ts) or datetime.now(UTC),
            run_id=event.run_id,
            actor=event.actor,
            action=event.action,
            entity_id=event.entity_id,
            reason=event.reason,
            payload_hash=event.payload_hash,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_audit_events(self, run_id: str) -> list[AuditEventRecord]:
        statement = (
            select(AuditEventRecord)
            .where(AuditEventRecord.run_id == run_id)
            .order_by(AuditEventRecord.ts)
        )
        return list(self.session.exec(statement).all())

    # --- Extraction Cache ---
    def get_extraction_cache(
        self, file_hash: str, model_id: str, prompt_version: str
    ) -> str | None:
        record = self.session.get(ExtractionCacheRecord, (file_hash, model_id, prompt_version))
        return record.response_json if record else None

    def put_extraction_cache(
        self, file_hash: str, model_id: str, prompt_version: str, response_json: str
    ) -> None:
        record = ExtractionCacheRecord(
            file_hash=file_hash,
            model_id=model_id,
            prompt_version=prompt_version,
            response_json=response_json,
        )
        self.session.merge(record)
        self.session.commit()

    # --- Egress Log ---
    def log_egress(self, log_record: EgressLogRecord) -> None:
        self.session.add(log_record)
        self.session.commit()

    def get_egress_logs(self, run_id: str | None = None) -> list[EgressLogRecord]:
        statement = select(EgressLogRecord)
        if run_id:
            statement = statement.where(EgressLogRecord.run_id == run_id)
        statement = statement.order_by(EgressLogRecord.ts)
        return list(self.session.exec(statement).all())
