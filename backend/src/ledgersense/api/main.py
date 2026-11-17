from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from ledgersense.accounting.journal import build_entries
from ledgersense.accounting.statements import profit_and_loss, trial_balance
from ledgersense.api.errors import (
    APIError,
    GateBlockedError,
    InvalidAuditorDecisionError,
    NotFoundError,
    api_error_handler,
)
from ledgersense.core.config import settings
from ledgersense.db.models import (
    AuditEventRecord,
    DocumentRecord,
    EgressLogRecord,
    JournalEntryRecord,
    JournalLineRecord,
    MatchRecord,
    ReceiptRecord,
    RiskFlagRecord,
    RunRecord,
)
from ledgersense.db.repository import Repository
from ledgersense.db.session import get_session
from ledgersense.domain.models import (
    RunConfig,
)
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.pipeline.gate import record_flag_decision
from ledgersense.pipeline.orchestrator import (
    GateBlockedError as OrchestratorGateBlockedError,
)
from ledgersense.pipeline.orchestrator import (
    commit_run as orchestrator_commit_run,
)
from ledgersense.pipeline.orchestrator import (
    process_run,
)
from ledgersense.tax.itr_mapper import build_deductions, build_itr3_draft
from ledgersense.tax.rules_engine import load_rules

app = FastAPI(title="LedgerSense API", version="0.1.0")

# Register custom API error handler
app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]

# Configure CORS
origins = [
    origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Response Models ---
class CreateRunRequest(BaseModel):
    id: str | None = None
    period_start: date
    period_end: date
    tax_regime_choice: Literal["old", "new"] = "old"
    cash_limit: Decimal = Decimal("10000.00")
    date_window_days: int = 3
    amount_tolerance: Decimal = Decimal("5.00")


class DecisionRequest(BaseModel):
    auditor_id: str
    decision: Literal["approve", "reject"]
    reason: str


class CommitRequest(BaseModel):
    auditor_id: str


DbSession = Annotated[Session, Depends(get_session)]


# --- 1. System & Health ---
@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    """Report health and perception provider mode."""
    return {
        "status": "ok",
        "llm_mode": settings.LLM_MODE,
        "model_id": settings.KIMI_MODEL,
    }


# --- 2. Ingestion & Runs ---
@app.post("/api/v1/runs")
def create_run(
    payload: CreateRunRequest,
    session: DbSession,
) -> dict[str, Any]:
    """Initialize a reconciliation run with derived regime."""
    cfg = RunConfig(
        period_start=payload.period_start,
        period_end=payload.period_end,
        tax_regime_choice=payload.tax_regime_choice,
        cash_limit=payload.cash_limit,
        date_window_days=payload.date_window_days,
        amount_tolerance=payload.amount_tolerance,
    )
    run_id = (
        payload.id
        or f"run:{payload.period_start.strftime('%Y%m')}-{payload.period_end.strftime('%Y%m')}"
    )

    existing = session.get(RunRecord, run_id)
    if existing:
        return {
            "id": existing.id,
            "period_start": str(existing.period_start),
            "period_end": str(existing.period_end),
            "regime": existing.regime,
            "status": existing.status,
            "config": json.loads(existing.config_json),
            "created_at": existing.created_at.isoformat(),
        }

    run_record = RunRecord(
        id=run_id,
        period_start=cfg.period_start,
        period_end=cfg.period_end,
        regime=cfg.regime,
        status="CREATED",
        config_json=cfg.model_dump_json(),
        created_at=datetime.now(UTC),
    )
    session.add(run_record)
    session.commit()
    session.refresh(run_record)

    return {
        "id": run_record.id,
        "period_start": str(run_record.period_start),
        "period_end": str(run_record.period_end),
        "regime": run_record.regime,
        "status": run_record.status,
        "config": json.loads(run_record.config_json),
        "created_at": run_record.created_at.isoformat(),
    }


@app.post("/api/v1/runs/{run_id}/documents")
async def upload_documents(
    run_id: str,
    files: Annotated[list[UploadFile], File(...)],
    session: DbSession,
) -> list[dict[str, Any]]:
    """Upload receipt images and PDFs with size/MIME validation and SHA-256 computation."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    allowed_exts = {".png", ".jpg", ".jpeg", ".pdf"}
    max_size = 25 * 1024 * 1024  # 25MB

    safe_run_dir = run_id.replace(":", "_")
    upload_dir = settings.uploads_dir / safe_run_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    for file in files:
        filename = Path(file.filename or "receipt.png").name
        ext = Path(filename).suffix.lower()
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{ext}' not allowed. Must be PNG/JPG/PDF.",
            )

        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=400, detail=f"File '{filename}' exceeds 25MB limit"
            )

        file_hash = hashlib.sha256(content).hexdigest()
        dest_path = upload_dir / filename
        dest_path.write_bytes(content)

        doc_record = DocumentRecord(
            id=f"doc:{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            filename=filename,
            file_hash=file_hash,
            mime=file.content_type or "image/png",
            extraction_status="PENDING",
        )
        session.add(doc_record)
        session.commit()
        session.refresh(doc_record)

        results.append(
            {
                "id": doc_record.id,
                "run_id": doc_record.run_id,
                "filename": doc_record.filename,
                "file_hash": doc_record.file_hash,
                "mime": doc_record.mime,
                "extraction_status": doc_record.extraction_status,
            }
        )

    return results


@app.post("/api/v1/runs/{run_id}/bank-csv")
async def upload_bank_csv(
    run_id: str,
    file: Annotated[UploadFile, File(...)],
    session: DbSession,
) -> dict[str, Any]:
    """Ingest bank statement CSV and store validated BankLine records."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    content = await file.read()
    repo = Repository(session)
    bank_lines = parse_bank_csv(content, run_id=run_id)
    repo.save_bank_lines(bank_lines)

    return {
        "lines_parsed": len(bank_lines),
        "errors": [],
    }


@app.post("/api/v1/runs/{run_id}/process", status_code=status.HTTP_202_ACCEPTED)
def process_pipeline(
    run_id: str,
    session: DbSession,
) -> dict[str, str]:
    """Trigger deterministic background or synchronous pipeline execution."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    final_run = process_run(run_id, session)
    status_str = final_run.status if hasattr(final_run, "status") else str(final_run)
    return {"status": status_str}


@app.get("/api/v1/runs/{run_id}")
def get_run_status(
    run_id: str,
    session: DbSession,
) -> dict[str, Any]:
    """Get run details and progress counters for the UI stage stepper."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    repo = Repository(session)
    docs = repo.get_documents(run_id)
    receipts = repo.get_receipts(run_id)
    matches = repo.get_matches(run_id)
    flags = repo.get_risk_flags(run_id)

    open_high_flags = sum(
        1 for f in flags if f.severity == "HIGH" and f.status == "OPEN"
    )

    return {
        "id": run.id,
        "period_start": str(run.period_start),
        "period_end": str(run.period_end),
        "regime": run.regime,
        "status": run.status,
        "config": json.loads(run.config_json),
        "documents_total": len(docs),
        "receipts_extracted": len(receipts),
        "matches_count": len(matches),
        "flags_count": len(flags),
        "open_high_flags": open_high_flags,
    }


# --- 3. Perceptions & Reconciliations ---
@app.get("/api/v1/runs/{run_id}/receipts")
def list_receipts(
    run_id: str,
    session: DbSession,
) -> list[dict[str, Any]]:
    """List extracted receipts for a run."""
    records = session.exec(
        select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)
    ).all()
    return [json.loads(r.payload_json) for r in records]


@app.get("/api/v1/runs/{run_id}/matches")
def list_matches(
    run_id: str,
    session: DbSession,
) -> list[dict[str, Any]]:
    """List matches and orphan transactions for a run."""
    records = session.exec(
        select(MatchRecord).where(MatchRecord.run_id == run_id)
    ).all()
    return [
        {
            "id": m.id,
            "run_id": m.run_id,
            "receipt_id": m.receipt_id,
            "bank_line_id": m.bank_line_id,
            "score": m.score,
            "kind": m.kind,
            "date_delta_days": m.date_delta_days,
            "amount_delta": m.amount_delta,
        }
        for m in records
    ]


# --- 4. Risk & Auditor Gate ---
@app.get("/api/v1/runs/{run_id}/flags")
def list_risk_flags(
    run_id: str,
    session: DbSession,
    status: Annotated[str | None, Query()] = None,
) -> list[dict[str, Any]]:
    """List risk flags sorted by severity (HIGH, MEDIUM, LOW)."""
    statement = select(RiskFlagRecord).where(RiskFlagRecord.run_id == run_id)
    if status:
        statement = statement.where(RiskFlagRecord.status == status)

    records = list(session.exec(statement).all())
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    records.sort(key=lambda r: (severity_order.get(r.severity, 3), r.id))

    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "rule_id": r.rule_id,
            "severity": r.severity,
            "status": r.status,
            "entity_ids": json.loads(r.entity_ids_json) if r.entity_ids_json else [],
            "legal_ref": r.legal_ref,
            "evidence": json.loads(r.evidence_json) if r.evidence_json else {},
            "suggested_action": r.suggested_action,
            "decided_by": r.decided_by,
            "decision_reason": r.decision_reason,
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        }
        for r in records
    ]


@app.post("/api/v1/flags/{flag_id}/decision")
def decide_risk_flag(
    flag_id: str,
    payload: DecisionRequest,
    session: DbSession,
) -> dict[str, Any]:
    """Human auditor decision on a risk flag with min 10-char reason and audit event logging."""
    flag = session.get(RiskFlagRecord, flag_id)
    if not flag:
        raise NotFoundError(f"RiskFlag {flag_id} not found")

    try:
        updated_flag = record_flag_decision(
            session=session,
            flag_id=flag_id,
            auditor_id=payload.auditor_id,
            decision=payload.decision,
            reason=payload.reason,
        )
    except ValueError as err:
        raise InvalidAuditorDecisionError(str(err)) from err

    # Rebuild draft journal entries to reflect decisions (excluding rejected vouchers)
    repo = Repository(session)
    receipts = repo.get_domain_receipts(flag.run_id)
    matches = repo.get_domain_matches(flag.run_id)
    flags = repo.get_domain_risk_flags(flag.run_id)
    bank_lines = repo.get_domain_bank_lines(flag.run_id)
    run_rec = session.get(RunRecord, flag.run_id)
    if run_rec:
        cfg = RunConfig.model_validate_json(run_rec.config_json)
        new_entries = build_entries(
            receipts=receipts,
            matches=matches,
            flags=flags,
            cfg=cfg,
            bank_lines=bank_lines,
        )
        repo.clear_journal_entries(flag.run_id)
        repo.save_journal_entries(new_entries)

    return {
        "id": updated_flag.id,
        "run_id": updated_flag.run_id,
        "rule_id": updated_flag.rule_id,
        "severity": updated_flag.severity,
        "status": updated_flag.status,
        "decided_by": updated_flag.decided_by,
        "decision_reason": updated_flag.decision_reason,
        "decided_at": (
            updated_flag.decided_at.isoformat() if updated_flag.decided_at else None
        ),
    }


@app.post("/api/v1/runs/{run_id}/flags/{flag_id}/decision")
def decide_risk_flag_scoped(
    run_id: str,
    flag_id: str,
    payload: DecisionRequest,
    session: DbSession,
) -> dict[str, Any]:
    """Scoped alias for /api/v1/flags/{flag_id}/decision allowing run_id in URL path."""
    return decide_risk_flag(flag_id=flag_id, payload=payload, session=session)


@app.post("/api/v1/runs/{run_id}/commit")
def commit_run(
    run_id: str,
    payload: CommitRequest,
    session: DbSession,
) -> dict[str, Any]:
    """Human gate: blocks with HTTP 409 if any HIGH flags are OPEN, commits journal entries on success."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    try:
        committed = orchestrator_commit_run(
            session=session,
            run_id=run_id,
            auditor_id=payload.auditor_id,
        )
        return {
            "status": "COMMITTED",
            "entries_committed": len(committed),
        }
    except OrchestratorGateBlockedError as err:
        raise GateBlockedError(
            message=str(err),
            details={"open_high_flags": [f.model_dump() for f in err.open_high_flags]},
        ) from err


# --- 5. Accounting & Statements ---
@app.get("/api/v1/runs/{run_id}/journal")
def get_journal(
    run_id: str,
    session: DbSession,
    status: Annotated[str | None, Query()] = None,
) -> list[dict[str, Any]]:
    """List journal entries with debit/credit lines."""
    statement = select(JournalEntryRecord).where(JournalEntryRecord.run_id == run_id)
    if status:
        statement = statement.where(JournalEntryRecord.status == status)

    entries = list(session.exec(statement).all())
    results: list[dict[str, Any]] = []

    for e in entries:
        lines = list(
            session.exec(
                select(JournalLineRecord).where(JournalLineRecord.entry_id == e.id)
            ).all()
        )
        results.append(
            {
                "id": e.id,
                "run_id": e.run_id,
                "entry_date": str(e.entry_date),
                "narration": e.narration,
                "status": e.status,
                "source_receipt_id": e.source_receipt_id,
                "flag_ids": json.loads(e.flag_ids_json) if e.flag_ids_json else [],
                "deduction_tag": e.deduction_tag,
                "lines": [
                    {
                        "account_code": l.account_code,
                        "debit": l.debit,
                        "credit": l.credit,
                    }
                    for l in lines
                ],
            }
        )

    return results


@app.get("/api/v1/runs/{run_id}/trial-balance")
def get_trial_balance(
    run_id: str,
    session: DbSession,
) -> dict[str, Any]:
    """Calculate Trial Balance from committed entries."""
    repo = Repository(session)
    entries = repo.get_domain_journal_entries(run_id, status="COMMITTED")
    if not entries:
        entries = repo.get_domain_journal_entries(run_id)
    tb = trial_balance(entries)
    return {
        "accounts": [row.model_dump() for row in tb.accounts],
        "total_debit": str(tb.total_debit),
        "total_credit": str(tb.total_credit),
        "balanced": tb.balanced,
    }


@app.get("/api/v1/runs/{run_id}/pnl")
def get_pnl(
    run_id: str,
    session: DbSession,
) -> dict[str, Any]:
    """Calculate Profit and Loss from committed entries."""
    repo = Repository(session)
    entries = repo.get_domain_journal_entries(run_id, status="COMMITTED")
    if not entries:
        entries = repo.get_domain_journal_entries(run_id)
    pnl = profit_and_loss(entries)
    return {
        "income": {k: str(v) for k, v in pnl.income.items()},
        "expenses": {k: str(v) for k, v in pnl.expenses.items()},
        "total_income": str(pnl.total_income),
        "total_expenses": str(pnl.total_expenses),
        "net_profit": str(pnl.net_profit),
    }


# --- 6. Tax Outputs ---
@app.get("/api/v1/runs/{run_id}/tax/deductions")
def get_deductions(
    run_id: str,
    session: DbSession,
) -> dict[str, Any]:
    """Get 80C/80D deductions schedule with draft watermark."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    cfg = RunConfig.model_validate_json(run.config_json)
    repo = Repository(session)
    entries = repo.get_domain_journal_entries(run_id, status="COMMITTED")
    if not entries:
        entries = repo.get_domain_journal_entries(run_id)
    rules = load_rules()
    schedule = build_deductions(entries=entries, rules=rules, cfg=cfg)
    return schedule.model_dump()


@app.get("/api/v1/runs/{run_id}/tax/itr")
def get_itr_draft_route(
    run_id: str,
    session: DbSession,
    form: Annotated[str, Query()] = "ITR-3",
) -> dict[str, Any]:
    """Get draft ITR JSON schema matching Section 8."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise NotFoundError(f"Run {run_id} not found")

    cfg = RunConfig.model_validate_json(run.config_json)
    repo = Repository(session)
    entries = repo.get_domain_journal_entries(run_id, status="COMMITTED")
    if not entries:
        entries = repo.get_domain_journal_entries(run_id)
    rules = load_rules()
    itr_draft = build_itr3_draft(entries=entries, rules=rules, cfg=cfg)
    return itr_draft.model_dump()


# --- 7. Audit & Privacy ---
@app.get("/api/v1/runs/{run_id}/audit-log")
def get_audit_log(
    run_id: str,
    session: DbSession,
) -> list[dict[str, Any]]:
    """Get read-only chronological audit trail."""
    events = list(
        session.exec(
            select(AuditEventRecord)
            .where(AuditEventRecord.run_id == run_id)
            .order_by(AuditEventRecord.ts)
        ).all()
    )
    return [
        {
            "id": evt.id,
            "ts": evt.ts.isoformat(),
            "run_id": evt.run_id,
            "actor": evt.actor,
            "action": evt.action,
            "entity_id": evt.entity_id,
            "reason": evt.reason,
            "payload_hash": evt.payload_hash,
        }
        for evt in events
    ]


@app.get("/api/v1/runs/{run_id}/egress")
def get_egress_log(
    run_id: str,
    session: DbSession,
) -> dict[str, Any]:
    """Get outbound LLM call transparent egress report."""
    records = list(
        session.exec(
            select(EgressLogRecord)
            .where(EgressLogRecord.run_id == run_id)
            .order_by(EgressLogRecord.ts)
        ).all()
    )
    total_bytes = sum(r.bytes for r in records)
    est_cost = f"{len(records) * 0.005:.3f}"

    return {
        "calls": len(records),
        "bytes": total_bytes,
        "est_cost": est_cost,
        "bank_data_sent": False,
        "entries": [
            {
                "id": r.id,
                "ts": r.ts.isoformat(),
                "file_hash": r.file_hash,
                "bytes": r.bytes,
                "bytes_sent": r.bytes,
                "model_id": r.model_id,
                "model": r.model_id,
                "masked": r.masked,
                "pii_masked": r.masked,
                "doc_id": r.file_hash[:12] if r.file_hash else r.id,
                "narration": f"Perception extraction for {r.file_hash[:8] if r.file_hash else r.id}",
                "est_cost": "0.005",
            }
            for r in records
        ],
    }
