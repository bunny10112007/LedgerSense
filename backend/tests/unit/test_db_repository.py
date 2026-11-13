from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import Session, SQLModel, create_engine

from ledgersense.db.models import DocumentRecord
from ledgersense.db.repository import Repository
from ledgersense.domain.models import (
    AuditEvent,
    BankLine,
    JournalEntry,
    JournalLine,
    LineItem,
    Match,
    Receipt,
    RiskFlag,
    Run,
    RunConfig,
)


@pytest.fixture
def repo():
    # In-memory SQLite with trigger
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TRIGGER trigger_abort_audit_events_update
                BEFORE UPDATE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is append-only: UPDATE forbidden');
                END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER trigger_abort_audit_events_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is append-only: DELETE forbidden');
                END;
                """
            )
        )
    with Session(engine) as session:
        yield Repository(session)


def test_db_run_lifecycle(repo: Repository):
    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        cash_limit=Decimal("10000.00"),
    )
    run = Run(
        id="run:test-01",
        period_start=cfg.period_start,
        period_end=cfg.period_end,
        regime=cfg.regime,
        config=cfg,
    )
    created = repo.create_run(run)
    assert created.id == "run:test-01"
    assert created.status == "CREATED"

    updated = repo.update_run_status("run:test-01", "AWAITING_REVIEW")
    assert updated is not None
    assert updated.status == "AWAITING_REVIEW"


def test_db_receipts_and_documents(repo: Repository):
    doc = DocumentRecord(
        id="doc:01",
        run_id="run:test-01",
        filename="g01.png",
        file_hash="hash01",
        mime="image/png",
    )
    repo.save_documents([doc])
    docs = repo.get_documents("run:test-01")
    assert len(docs) == 1

    rcpt = Receipt(
        id="rcpt:01",
        run_id="run:test-01",
        source_file="g01.png",
        file_hash="hash01",
        vendor_key="aravali|08AAAFA1234B1ZC",
        doc_type="gst_invoice",
        line_items=[LineItem(description="Item", amount=Decimal("100.00"))],
        total=Decimal("100.00"),
    )
    repo.save_receipts([rcpt])
    receipts = repo.get_receipts("run:test-01")
    assert len(receipts) == 1
    assert receipts[0].vendor_key == "aravali|08AAAFA1234B1ZC"


def test_db_bank_lines_and_matches(repo: Repository):
    line = BankLine(
        id="bank:01",
        run_id="run:test-01",
        txn_date=date(2025, 6, 12),
        narration="UPI/PAY",
        debit=Decimal("100.00"),
    )
    repo.save_bank_lines([line])
    lines = repo.get_bank_lines("run:test-01")
    assert len(lines) == 1

    match = Match(
        id="match:01",
        run_id="run:test-01",
        receipt_id="rcpt:01",
        bank_line_id="bank:01",
        score=0.95,
        kind="MATCHED",
    )
    repo.save_matches([match])
    matches = repo.get_matches("run:test-01")
    assert len(matches) == 1
    assert matches[0].score == 0.95


def test_db_risk_flags_and_decisions(repo: Repository):
    flag = RiskFlag(
        id="flag:01",
        run_id="run:test-01",
        rule_id="CASH_LIMIT",
        severity="HIGH",
        entity_ids=["rcpt:G09"],
        evidence={"amount": "12000.00"},
        suggested_action="Disallow",
    )
    repo.save_risk_flags([flag])
    flags = repo.get_risk_flags("run:test-01")
    assert len(flags) == 1
    assert flags[0].status == "OPEN"

    updated = repo.update_risk_flag_decision(
        flag_id="flag:01",
        decided_by="auditor-a",
        decision="approve",
        reason="Valid emergency cash purchase",
    )
    assert updated is not None
    assert updated.status == "APPROVED"
    assert updated.decided_by == "auditor-a"


def test_db_journal_entries(repo: Repository):
    je = JournalEntry(
        id="je:01",
        run_id="run:test-01",
        entry_date=date(2025, 6, 12),
        narration="Office supplies",
        lines=[
            JournalLine(account_code="EXP", debit=Decimal("100.00")),
            JournalLine(account_code="BANK", credit=Decimal("100.00")),
        ],
    )
    repo.save_journal_entries([je])
    entries = repo.get_journal_entries("run:test-01")
    assert len(entries) == 1
    assert entries[0].narration == "Office supplies"


def test_audit_events_append_only_trigger(repo: Repository):
    event = AuditEvent(
        id="evt:01",
        ts=date(2025, 6, 12),
        run_id="run:test-01",
        actor="system",
        action="STATE_CHANGE",
        payload_hash="sha256hash",
    )
    created = repo.append_audit_event(event)
    assert created.id == "evt:01"

    # Attempting to UPDATE an audit event must fail due to trigger
    with pytest.raises((IntegrityError, OperationalError), match="append-only: UPDATE forbidden"):
        repo.session.execute(
            text("UPDATE audit_events SET action = 'MUTATED' WHERE id = 'evt:01'")
        )

    # Attempting to DELETE an audit event must fail due to trigger
    with pytest.raises((IntegrityError, OperationalError), match="append-only: DELETE forbidden"):
        repo.session.execute(
            text("DELETE FROM audit_events WHERE id = 'evt:01'")
        )
