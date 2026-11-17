from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import Session, SQLModel, create_engine

from ledgersense.accounting.chart import (
    BANK,
    CASH,
    EXP_DINING,
    EXP_FUEL,
    EXP_GENERAL,
    EXP_OFFICE,
    EXP_SOFTWARE,
)
from ledgersense.accounting.statements import profit_and_loss, trial_balance
from ledgersense.audit.log import (
    append as append_audit,
)
from ledgersense.audit.log import (
    compute_payload_hash,
    get_events,
)
from ledgersense.audit.log import (
    delete as delete_audit,
)
from ledgersense.audit.log import (
    update as update_audit,
)
from ledgersense.domain.models import (
    AuditEvent,
    JournalEntry,
    JournalLine,
    quantize_money,
)

# Strategy for generating positive monetary amounts quantized to 0.01
money_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("100000.00"),
    places=2,
)

expense_accounts_strategy = st.sampled_from(
    [EXP_OFFICE, EXP_FUEL, EXP_SOFTWARE, EXP_DINING, EXP_GENERAL]
)
credit_accounts_strategy = st.sampled_from([BANK, CASH])


@st.composite
def balanced_journal_entry_strategy(draw: st.DrawFn) -> JournalEntry:
    """Generate a balanced, valid JournalEntry with status COMMITTED."""
    amt1 = draw(money_strategy)
    split = draw(st.booleans())

    exp_acct1 = draw(expense_accounts_strategy)
    credit_acct = draw(credit_accounts_strategy)

    if split:
        amt2 = draw(money_strategy)
        total_credit = quantize_money(amt1 + amt2)
        exp_acct2 = draw(expense_accounts_strategy)
        lines = [
            JournalLine(account_code=exp_acct1, debit=amt1, credit=Decimal("0.00")),
            JournalLine(account_code=exp_acct2, debit=amt2, credit=Decimal("0.00")),
            JournalLine(account_code=credit_acct, debit=Decimal("0.00"), credit=total_credit),
        ]
    else:
        lines = [
            JournalLine(account_code=exp_acct1, debit=amt1, credit=Decimal("0.00")),
            JournalLine(account_code=credit_acct, debit=Decimal("0.00"), credit=amt1),
        ]

    return JournalEntry(
        id=f"je:{draw(st.integers(min_value=1, max_value=99999)):05d}",
        run_id="run:hypo-test",
        entry_date=date(2025, 6, 15),
        narration="Hypothesis test journal entry",
        lines=lines,
        status="COMMITTED",
    )


# --- 1. Hypothesis Property Test on Trial Balance ---


@given(st.lists(balanced_journal_entry_strategy(), min_size=1, max_size=25))
def test_hypothesis_trial_balance_always_balanced(entries: list[JournalEntry]) -> None:
    """Property test: Any collection of valid balanced committed entries yields a perfectly balanced Trial Balance."""
    tb = trial_balance(entries)
    assert tb.balanced is True
    assert tb.total_debit == tb.total_credit
    assert tb.total_debit >= Decimal("0.00")

    pnl = profit_and_loss(entries)
    assert pnl.total_income == Decimal("0.00")
    assert pnl.total_expenses == tb.total_debit
    assert pnl.net_profit == -tb.total_debit


# --- 2. Unit Tests for JournalEntry Validation ---


def test_journal_entry_rejects_unbalanced_lines() -> None:
    with pytest.raises(ValidationError, match="total debit .* != total credit"):
        JournalEntry(
            id="je:0001",
            run_id="run:demo",
            entry_date=date(2025, 6, 1),
            narration="Unbalanced test entry",
            lines=[
                JournalLine(account_code=EXP_OFFICE, debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalLine(account_code=BANK, debit=Decimal("0.00"), credit=Decimal("90.00")),
            ],
        )


def test_journal_entry_rejects_single_line() -> None:
    with pytest.raises(ValidationError, match="at least 2 lines"):
        JournalEntry(
            id="je:0002",
            run_id="run:demo",
            entry_date=date(2025, 6, 1),
            narration="Single line test entry",
            lines=[
                JournalLine(account_code=EXP_OFFICE, debit=Decimal("50.00"), credit=Decimal("50.00")),
            ],
        )


# --- 3. Unit Tests for Append-Only Audit Log ---


@pytest.fixture
def in_memory_db_session():
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(test_engine)
    with test_engine.begin() as conn:
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
    with Session(test_engine) as session:
        yield session


def test_audit_log_append_and_payload_hash(in_memory_db_session: Session) -> None:
    payload = {"status": "APPROVED", "auditor": "auditor-a", "reason": "Verified genuine invoice"}
    hash1 = compute_payload_hash(payload)
    hash2 = compute_payload_hash(payload)
    assert hash1 == hash2  # Deterministic hash

    evt = AuditEvent(
        id="evt:test-0001",
        ts=datetime.now(),
        run_id="run:audit-test",
        actor="auditor-a",
        action="FLAG_APPROVED",
        entity_id="flag:0001",
        reason="Verified genuine invoice",
        payload_hash=hash1,
    )
    saved = append_audit(evt, session=in_memory_db_session)
    assert saved.id == "evt:test-0001"

    events = get_events("run:audit-test", session=in_memory_db_session)
    assert len(events) == 1
    assert events[0].payload_hash == hash1


def test_audit_log_immutability_triggers(in_memory_db_session: Session) -> None:
    evt = AuditEvent(
        id="evt:test-0002",
        ts=datetime.now(),
        run_id="run:audit-test",
        actor="system",
        action="STATE_CHANGE",
        payload_hash="somehash",
    )
    append_audit(evt, session=in_memory_db_session)

    # SQLite trigger blocks UPDATE
    with pytest.raises((IntegrityError, OperationalError), match="append-only: UPDATE forbidden"):
        in_memory_db_session.execute(
            text("UPDATE audit_events SET action = 'ALTERED' WHERE id = 'evt:test-0002'")
        )

    # SQLite trigger blocks DELETE
    with pytest.raises((IntegrityError, OperationalError), match="append-only: DELETE forbidden"):
        in_memory_db_session.execute(
            text("DELETE FROM audit_events WHERE id = 'evt:test-0002'")
        )

    # Python helpers forbid UPDATE and DELETE
    with pytest.raises(NotImplementedError, match="UPDATE is forbidden"):
        update_audit()

    with pytest.raises(NotImplementedError, match="DELETE is forbidden"):
        delete_audit()
