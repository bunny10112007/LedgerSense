from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from ledgersense.accounting.statements import trial_balance
from ledgersense.core.config import settings
from ledgersense.db.repository import Repository
from ledgersense.domain.models import Run, RunConfig
from ledgersense.pipeline.gate import record_flag_decision
from ledgersense.pipeline.orchestrator import GateBlockedError, commit_run, process_run


@pytest.fixture
def isolated_db_session():
    """Create a completely isolated in-memory SQLite database with append-only triggers."""
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


def test_pipeline_integration_e2e(
    isolated_db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end golden acceptance test for vertical slice pipeline integration in replay mode."""
    # Ensure zero network calls via replay mode
    monkeypatch.setattr(settings, "LLM_MODE", "replay")

    session = isolated_db_session
    repo = Repository(session)

    run_id = "run:2025-26-demo"
    golden_dir = Path(__file__).resolve().parents[3] / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    bank_csv_path = golden_dir / "bank.csv"

    receipt_paths = sorted(receipts_dir.glob("*.png"))
    assert len(receipt_paths) == 16

    # 1. Initialize Run entity in CREATED status
    cfg = RunConfig(
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        date_window_days=3,
        amount_tolerance=Decimal("5.00"),
        cash_limit=Decimal("10000.00"),
    )
    initial_run = Run(
        id=run_id,
        period_start=cfg.period_start,
        period_end=cfg.period_end,
        regime=cfg.regime,
        status="CREATED",
        config=cfg,
    )
    repo.create_run(initial_run)

    # 2. Run process_run end-to-end
    run = process_run(
        session=session,
        run_id=run_id,
        receipt_paths=receipt_paths,
        bank_csv_path=bank_csv_path,
    )

    # Assert milestone reached: AWAITING_REVIEW because 4 HIGH flags remain OPEN
    assert run.status == "AWAITING_REVIEW"

    # Assert 16 receipts persisted
    receipts = repo.get_domain_receipts(run_id)
    assert len(receipts) == 16

    # Assert matches persisted: 13 MATCHED + 1 UNMATCHED_BANK
    matches = repo.get_domain_matches(run_id)
    matched_pairs = [m for m in matches if m.kind == "MATCHED"]
    unmatched_bank = [m for m in matches if m.kind == "UNMATCHED_BANK"]
    assert len(matched_pairs) == 13
    assert len(unmatched_bank) == 1

    # Assert 7 risk flags persisted (4 HIGH, 3 MEDIUM)
    flags = repo.get_domain_risk_flags(run_id)
    assert len(flags) == 7
    high_flags = [f for f in flags if f.severity == "HIGH"]
    medium_flags = [f for f in flags if f.severity == "MEDIUM"]
    assert len(high_flags) == 4
    assert len(medium_flags) == 3

    # 3. Gate verification: attempting commit_run while 4 HIGH flags are OPEN must raise GateBlockedError
    with pytest.raises(GateBlockedError) as exc_info:
        commit_run(session=session, run_id=run_id, auditor_id="auditor-a")

    assert len(exc_info.value.open_high_flags) == 4
    blocked_rules = {f.rule_id for f in exc_info.value.open_high_flags}
    assert blocked_rules == {"DUP_FARE", "OUT_OF_PERIOD", "CASH_LIMIT", "GSTIN_INVALID"}

    # 4. Auditor sign-off: resolve the 4 HIGH severity risk flags
    flag_dup = next(f for f in high_flags if f.rule_id == "DUP_FARE")
    flag_oop = next(f for f in high_flags if f.rule_id == "OUT_OF_PERIOD")
    flag_cash = next(f for f in high_flags if f.rule_id == "CASH_LIMIT")
    flag_gstin = next(f for f in high_flags if f.rule_id == "GSTIN_INVALID")

    # Reject duplicate and out-of-period vouchers
    record_flag_decision(
        session=session,
        flag_id=flag_dup.id,
        auditor_id="auditor-a",
        decision="reject",
        reason="Confirmed duplicate of G05 fare voucher; rejected",
    )
    record_flag_decision(
        session=session,
        flag_id=flag_oop.id,
        auditor_id="auditor-a",
        decision="reject",
        reason="Invoice date falls into next financial year; rejected for FY25-26",
    )

    # Approve cash limit and invalid GSTIN (gross booking without ITC)
    record_flag_decision(
        session=session,
        flag_id=flag_cash.id,
        auditor_id="auditor-a",
        decision="approve",
        reason="Verified genuine cash emergency expense with supporting receipt",
    )
    record_flag_decision(
        session=session,
        flag_id=flag_gstin.id,
        auditor_id="auditor-a",
        decision="approve",
        reason="Approved booking expense gross with ITC blocked due to invalid GSTIN",
    )

    # 5. Assert run status automatically transitions to APPROVED once all HIGH flags are resolved
    approved_run = repo.get_domain_run(run_id)
    assert approved_run is not None
    assert approved_run.status == "APPROVED"

    # 6. Execute commit_run after gate approval
    committed_entries = commit_run(
        session=session,
        run_id=run_id,
        auditor_id="auditor-a",
    )

    # Assert exactly 14 entries committed
    assert len(committed_entries) == 14
    committed_run = repo.get_domain_run(run_id)
    assert committed_run is not None
    assert committed_run.status == "COMMITTED"

    # 7. Verify Trial Balance on committed entries
    tb = trial_balance(committed_entries)
    assert tb.balanced is True
    assert tb.total_debit == tb.total_credit == Decimal("131880.00")

    # 8. Verify the complete chronological audit trail
    audit_events = repo.get_domain_audit_events(run_id)
    actions = [e.action for e in audit_events]

    # Extraction milestone events
    assert any(a in ("EXTRACTION", "LLM_CALL") for a in actions)
    # State transitions
    assert "STATE_CHANGE" in actions
    # Flag decisions
    assert "FLAG_REJECT" in actions
    assert "FLAG_APPROVE" in actions
    # Final commitment
    assert "RUN_COMMITTED" in actions
