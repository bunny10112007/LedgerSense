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
    BankLineRecord,
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
    BankLine,
    Receipt,
    RiskFlag,
    RunConfig,
)
from ledgersense.matching.bank_csv import parse as parse_bank_csv
from ledgersense.pipeline.adapters import (
    build_deductions_schedule,
    build_draft_journal_entries,
    build_itr_draft,
    calculate_pnl,
    calculate_trial_balance,
)
from ledgersense.pipeline.gate import can_commit
from ledgersense.pipeline.orchestrator import process_run
from ledgersense.pipeline.state_machine import transition_run_status

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

    final_status = process_run(run_id, session)
    return {"status": final_status}


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
    if payload.auditor_id not in ("auditor-a", "auditor-b"):
        raise InvalidAuditorDecisionError(
            f"Invalid auditor_id '{payload.auditor_id}'. Must be 'auditor-a' or 'auditor-b'."
        )
    if len(payload.reason.strip()) < 10:
        raise InvalidAuditorDecisionError(
            "Decision reason must be at least 10 characters long."
        )

    flag = session.get(RiskFlagRecord, flag_id)
    if not flag:
        raise NotFoundError(f"RiskFlag {flag_id} not found")

    new_status = "APPROVED" if payload.decision.lower() == "approve" else "REJECTED"
    flag.status = new_status
    flag.decided_by = payload.auditor_id
    flag.decision_reason = payload.reason
    flag.decided_at = datetime.now(UTC)
    session.add(flag)

    # Write append-only AuditEvent
    action = "FLAG_APPROVED" if new_status == "APPROVED" else "FLAG_REJECTED"
    payload_hash = hashlib.sha256(
        f"{flag_id}:{new_status}:{payload.reason}".encode()
    ).hexdigest()
    audit_event = AuditEventRecord(
        id=f"evt:{uuid.uuid4().hex[:12]}",
        ts=datetime.now(UTC),
        run_id=flag.run_id,
        actor=payload.auditor_id,
        action=action,
        entity_id=flag_id,
        reason=payload.reason,
        payload_hash=payload_hash,
    )
    session.add(audit_event)
    session.commit()
    session.refresh(flag)

    # Re-evaluate run state: if all HIGH flags resolved, transition AWAITING_REVIEW -> APPROVED
    all_flags = list(
        session.exec(
            select(RiskFlagRecord).where(RiskFlagRecord.run_id == flag.run_id)
        ).all()
    )
    has_open_high = any(f.severity == "HIGH" and f.status == "OPEN" for f in all_flags)
    run = session.get(RunRecord, flag.run_id)

    if run and not has_open_high and run.status == "AWAITING_REVIEW":
        transition_run_status(
            flag.run_id,
            "APPROVED",
            session,
            actor="system",
            reason="All HIGH severity risk flags resolved by auditor sign-off",
        )

        # Rebuild/update draft journal entries to reflect rejected or approved out-of-period/duplicate receipts
        receipt_records = list(
            session.exec(
                select(ReceiptRecord).where(ReceiptRecord.run_id == flag.run_id)
            ).all()
        )
        receipts = [
            Receipt.model_validate_json(r.payload_json) for r in receipt_records
        ]
        bank_records = list(
            session.exec(
                select(BankLineRecord).where(BankLineRecord.run_id == flag.run_id)
            ).all()
        )
        bank_lines = [
            BankLine(
                id=b.id,
                run_id=b.run_id,
                txn_date=b.txn_date,
                narration=b.narration,
                debit=Decimal(b.debit),
                credit=Decimal(b.credit),
                balance=Decimal(b.balance) if b.balance else None,
                ref_no=b.ref_no,
            )
            for b in bank_records
        ]
        active_flags = [
            RiskFlag(
                id=f.id,
                run_id=f.run_id,
                rule_id=f.rule_id,
                severity=f.severity,  # type: ignore[arg-type]
                entity_ids=json.loads(f.entity_ids_json) if f.entity_ids_json else [],
                legal_ref=f.legal_ref,
                evidence=json.loads(f.evidence_json) if f.evidence_json else {},
                suggested_action=f.suggested_action,
                status=f.status,  # type: ignore[arg-type]
                decided_by=f.decided_by,
                decision_reason=f.decision_reason,
                decided_at=f.decided_at,
            )
            for f in all_flags
        ]
        new_entries = build_draft_journal_entries(
            flag.run_id, receipts, bank_lines, active_flags
        )

        # Delete old draft entries and store updated ones
        old_entries = list(
            session.exec(
                select(JournalEntryRecord)
                .where(JournalEntryRecord.run_id == flag.run_id)
                .where(JournalEntryRecord.status == "DRAFT")
            ).all()
        )
        old_entry_ids = [e.id for e in old_entries]
        if old_entry_ids:
            old_lines = list(
                session.exec(
                    select(JournalLineRecord).where(
                        JournalLineRecord.entry_id.in_(old_entry_ids)
                    )
                ).all()
            )
            for ol in old_lines:
                session.delete(ol)
            for oe in old_entries:
                session.delete(oe)
            session.commit()

        repo = Repository(session)
        repo.save_journal_entries(new_entries)

    return {
        "id": flag.id,
        "run_id": flag.run_id,
        "rule_id": flag.rule_id,
        "severity": flag.severity,
        "status": flag.status,
        "decided_by": flag.decided_by,
        "decision_reason": flag.decision_reason,
        "decided_at": flag.decided_at.isoformat() if flag.decided_at else None,
    }


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

    allowed, open_high_flags = can_commit(run_id, session)
    if not allowed:
        raise GateBlockedError(
            message="Cannot commit while HIGH risk flags are open",
            details={"open_high_flags": [f.model_dump() for f in open_high_flags]},
        )

    # Transition eligible DRAFT journal entries to COMMITTED
    draft_entries = list(
        session.exec(
            select(JournalEntryRecord)
            .where(JournalEntryRecord.run_id == run_id)
            .where(JournalEntryRecord.status == "DRAFT")
        ).all()
    )
    for entry in draft_entries:
        entry.status = "COMMITTED"
        session.add(entry)

    transition_run_status(
        run_id,
        "COMMITTED",
        session,
        actor=payload.auditor_id,
        reason=f"Run committed and entries locked by {payload.auditor_id}",
    )

    payload_hash = hashlib.sha256(
        f"{run_id}:COMMITTED:{len(draft_entries)}".encode()
    ).hexdigest()
    audit_event = AuditEventRecord(
        id=f"evt:{uuid.uuid4().hex[:12]}",
        ts=datetime.now(UTC),
        run_id=run_id,
        actor=payload.auditor_id,
        action="RUN_COMMITTED",
        entity_id=run_id,
        reason=f"Committed {len(draft_entries)} journal entries",
        payload_hash=payload_hash,
    )
    session.add(audit_event)
    session.commit()

    return {
        "status": "COMMITTED",
        "entries_committed": len(draft_entries),
    }


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
    tb = calculate_trial_balance(run_id, session)
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
    pnl = calculate_pnl(run_id, session)
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
    schedule = build_deductions_schedule(run_id, cfg, session)
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
    itr_draft = build_itr_draft(run_id, form, cfg, session)
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
                "model_id": r.model_id,
                "masked": r.masked,
            }
            for r in records
        ],
    }
