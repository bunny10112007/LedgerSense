from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

import ledgersense.db.session
from ledgersense.api.main import app
from ledgersense.core.config import settings
from ledgersense.db.session import get_session


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure clean isolated database and replay mode forced for tests."""
    test_db = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(test_engine)
    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS trigger_abort_audit_events_update
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
                CREATE TRIGGER IF NOT EXISTS trigger_abort_audit_events_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is append-only: DELETE forbidden');
                END;
                """
            )
        )

    def _get_test_session():
        with Session(test_engine) as session:
            yield session

    monkeypatch.setattr(ledgersense.db.session, "engine", test_engine)
    app.dependency_overrides[get_session] = _get_test_session
    monkeypatch.setattr(settings, "LLM_MODE", "replay")
    monkeypatch.setattr(
        settings.__class__, "uploads_dir", property(lambda self: tmp_path / "uploads")
    )
    yield
    app.dependency_overrides.clear()


def test_full_pipeline_api_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration test executing the full 18-route lifecycle on golden receipts and bank CSV."""
    monkeypatch.setattr(settings, "LLM_MODE", "replay")
    client = TestClient(app)

    golden_dir = Path(__file__).resolve().parents[3] / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    bank_csv_path = golden_dir / "bank.csv"

    # 1. Health check
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    health_data = resp.json()
    assert health_data["status"] == "ok"
    assert health_data["llm_mode"] == "replay"

    # 2. Create Run
    create_run_payload = {
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "tax_regime_choice": "old",
    }
    resp = client.post("/api/v1/runs", json=create_run_payload)
    assert resp.status_code == 200, resp.text
    run_data = resp.json()
    run_id = run_data["id"]
    assert run_data["regime"] == "ITA_1961"
    assert run_data["status"] == "CREATED"

    # 3. Upload 16 Golden Documents
    png_files = sorted(receipts_dir.glob("*.png"))
    assert len(png_files) == 16
    files_payload = [
        ("files", (png_path.name, png_path.read_bytes(), "image/png"))
        for png_path in png_files
    ]
    resp = client.post(f"/api/v1/runs/{run_id}/documents", files=files_payload)
    assert resp.status_code == 200, resp.text
    docs_data = resp.json()
    assert len(docs_data) == 16

    # 4. Upload Bank CSV
    with open(bank_csv_path, "rb") as f:
        resp = client.post(
            f"/api/v1/runs/{run_id}/bank-csv",
            files={"file": ("bank.csv", f.read(), "text/csv")},
        )
    assert resp.status_code == 200, resp.text
    csv_resp = resp.json()
    assert csv_resp["lines_parsed"] == 16

    # 5. Process Run
    resp = client.post(f"/api/v1/runs/{run_id}/process")
    assert resp.status_code in (200, 202), resp.text

    # 6. Get Run with progress counters
    resp = client.get(f"/api/v1/runs/{run_id}")
    assert resp.status_code == 200
    run_status_data = resp.json()
    assert run_status_data["status"] == "AWAITING_REVIEW"
    assert run_status_data["documents_total"] == 16
    assert run_status_data["receipts_extracted"] == 16
    assert run_status_data["open_high_flags"] == 4

    # 7. Get Receipts
    resp = client.get(f"/api/v1/runs/{run_id}/receipts")
    assert resp.status_code == 200
    receipts_list = resp.json()
    assert len(receipts_list) == 16

    # 8. Get Matches
    resp = client.get(f"/api/v1/runs/{run_id}/matches")
    assert resp.status_code == 200
    matches_list = resp.json()
    assert len(matches_list) == 14  # 13 matched + 1 unmatched bank debit

    # 9. Get Risk Flags
    resp = client.get(f"/api/v1/runs/{run_id}/flags?status=OPEN")
    assert resp.status_code == 200
    flags_list = resp.json()
    assert len(flags_list) == 7
    # Verify severity sort: HIGH first
    assert flags_list[0]["severity"] == "HIGH"
    high_flags = [f for f in flags_list if f["severity"] == "HIGH"]
    assert len(high_flags) == 4

    # 10. Commit Gate: Must block with HTTP 409 while HIGH flags are open
    resp = client.post(
        f"/api/v1/runs/{run_id}/commit", json={"auditor_id": "auditor-a"}
    )
    assert resp.status_code == 409
    err_body = resp.json()
    assert "HIGH" in err_body["code"] or err_body["code"] == "GATE_BLOCKED_HIGH_RISK"
    assert len(err_body["details"]["open_high_flags"]) == 4

    # 11. Flag Decision Validation: Reject short reason (< 10 chars)
    first_high_flag = high_flags[0]
    bad_decision_resp = client.post(
        f"/api/v1/flags/{first_high_flag['id']}/decision",
        json={"auditor_id": "auditor-a", "decision": "approve", "reason": "too short"},
    )
    assert bad_decision_resp.status_code == 422

    # Resolve all 4 open HIGH risk flags
    decisions = [
        ("DUP_FARE", "reject", "Reject duplicate cab fare receipt"),
        ("OUT_OF_PERIOD", "reject", "Postpone to next financial year 2026-27"),
        ("CASH_LIMIT", "approve", "Board approved urgent hardware cash expense"),
        (
            "GSTIN_INVALID",
            "approve",
            "Verified valid merchant with offline registration",
        ),
    ]
    for rule_id, dec, reason in decisions:
        flag_to_resolve = next(f for f in high_flags if f["rule_id"] == rule_id)
        dec_resp = client.post(
            f"/api/v1/flags/{flag_to_resolve['id']}/decision",
            json={"auditor_id": "auditor-a", "decision": dec, "reason": reason},
        )
        assert dec_resp.status_code == 200, dec_resp.text
        assert dec_resp.json()["status"] in ("APPROVED", "REJECTED")

    # Run status must now be APPROVED
    resp = client.get(f"/api/v1/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"
    assert resp.json()["open_high_flags"] == 0

    # 12. Commit Gate: Must now succeed with HTTP 200
    commit_resp = client.post(
        f"/api/v1/runs/{run_id}/commit", json={"auditor_id": "auditor-a"}
    )
    assert commit_resp.status_code == 200, commit_resp.text
    commit_data = commit_resp.json()
    assert commit_data["status"] == "COMMITTED"
    assert commit_data["entries_committed"] > 0

    # 13. Journal Entries: Now COMMITTED
    resp = client.get(f"/api/v1/runs/{run_id}/journal?status=COMMITTED")
    assert resp.status_code == 200
    journal_entries = resp.json()
    assert len(journal_entries) > 0
    for entry in journal_entries:
        assert entry["status"] == "COMMITTED"
        assert len(entry["lines"]) >= 2

    # 14. Trial Balance
    resp = client.get(f"/api/v1/runs/{run_id}/trial-balance")
    assert resp.status_code == 200
    tb = resp.json()
    assert tb["balanced"] is True
    assert tb["total_debit"] == tb["total_credit"]

    # 15. PnL Statement
    resp = client.get(f"/api/v1/runs/{run_id}/pnl")
    assert resp.status_code == 200
    pnl = resp.json()
    assert "net_profit" in pnl or "net" in pnl

    # 16. Tax Deductions (80C / 80D)
    resp = client.get(f"/api/v1/runs/{run_id}/tax/deductions")
    assert resp.status_code == 200
    deductions = resp.json()
    assert deductions["label"] == "Draft schedule"
    assert (
        "80C" in [item["section"] for item in deductions.get("items", [])]
        or "80C" in deductions
    )

    # 17. Tax ITR Draft
    resp = client.get(f"/api/v1/runs/{run_id}/tax/itr?form=ITR3")
    assert resp.status_code == 200
    itr = resp.json()
    assert itr["label"] == "Draft JSON in LedgerSense schema"
    assert itr["form"] in ("ITR-3", "ITR3")

    # 18. Audit Log & Egress
    resp = client.get(f"/api/v1/runs/{run_id}/audit-log")
    assert resp.status_code == 200
    audit_events = resp.json()
    actions = [e["action"] for e in audit_events]
    assert "STATE_CHANGE" in actions
    assert any(
        a in ("FLAG_APPROVED", "FLAG_REJECTED", "FLAG_APPROVE", "FLAG_REJECT")
        for a in actions
    )
    assert "RUN_COMMITTED" in actions

    resp = client.get(f"/api/v1/runs/{run_id}/egress")
    assert resp.status_code == 200
    egress_data = resp.json()
    assert egress_data["bank_data_sent"] is False
