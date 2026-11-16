from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlmodel import Session

from ledgersense.audit.log import compute_payload_hash
from ledgersense.db.repository import Repository
from ledgersense.domain.models import AuditEvent, RiskFlag
from ledgersense.pipeline.state_machine import transition_run

ALLOWED_AUDITORS: frozenset[str] = frozenset({"auditor-a", "auditor-b"})


def can_commit(flags: list[RiskFlag]) -> tuple[bool, list[RiskFlag]]:
    """Determine whether a run can commit based on HIGH severity OPEN flags.

    Returns:
    - (False, open_high_flags) if any HIGH severity risk flag remains OPEN.
    - (True, []) when zero HIGH severity risk flags are OPEN.
    """
    open_high = [f for f in flags if f.severity == "HIGH" and f.status == "OPEN"]
    return (len(open_high) == 0, open_high)


def check_run_gate(session: Session, run_id: str) -> tuple[bool, list[RiskFlag]]:
    """Check the commit gate for a run in the database."""
    repo = Repository(session)
    flags = repo.get_domain_risk_flags(run_id)
    return can_commit(flags)


def record_flag_decision(
    session: Session,
    flag_id: str,
    auditor_id: str,
    decision: Literal["approve", "reject"] | str,
    reason: str,
) -> RiskFlag:
    """Record an auditor decision on a risk flag with validation and audit logging.

    Validates:
    - auditor_id in {"auditor-a", "auditor-b"}
    - len(reason.strip()) >= 10
    - decision in {"approve", "reject"}

    Appends an AuditEvent.
    If all HIGH flags for the run are now resolved and run is in AWAITING_REVIEW,
    automatically transitions the run status to APPROVED.
    """
    if auditor_id not in ALLOWED_AUDITORS:
        raise ValueError(f"Invalid auditor ID '{auditor_id}'. Allowed: {sorted(ALLOWED_AUDITORS)}")

    clean_reason = reason.strip()
    if len(clean_reason) < 10:
        raise ValueError(
            f"Auditor decision reason must be at least 10 characters (got {len(clean_reason)})."
        )

    clean_decision = decision.strip().lower()
    if clean_decision not in ("approve", "reject"):
        raise ValueError(f"Invalid decision '{decision}'. Must be 'approve' or 'reject'.")

    repo = Repository(session)
    flag_record = repo.update_risk_flag_decision(
        flag_id=flag_id,
        decided_by=auditor_id,
        decision=clean_decision,
        reason=clean_reason,
    )
    if not flag_record:
        raise ValueError(f"RiskFlag '{flag_id}' not found")

    # Record Audit Event
    action = f"FLAG_{clean_decision.upper()}"
    evt = AuditEvent(
        id=f"evt:{uuid4().hex[:12]}",
        ts=datetime.now(UTC),
        run_id=flag_record.run_id,
        actor=auditor_id,
        action=action,
        entity_id=flag_id,
        reason=clean_reason,
        payload_hash=compute_payload_hash(
            {
                "flag_id": flag_id,
                "decision": clean_decision,
                "reason": clean_reason,
                "auditor_id": auditor_id,
            }
        ),
    )
    repo.append_audit_event(evt)

    # Check if all HIGH flags for the run are now resolved
    all_flags = repo.get_domain_risk_flags(flag_record.run_id)
    can_commit_now, _ = can_commit(all_flags)
    if can_commit_now:
        run_record = repo.get_run(flag_record.run_id)
        if run_record and run_record.status == "AWAITING_REVIEW":
            transition_run(
                session=session,
                run_id=flag_record.run_id,
                target="APPROVED",
                actor=auditor_id,
                reason="All HIGH risk flags resolved by auditor decision",
            )

    # Retrieve and return updated RiskFlag domain object
    matching_flags = [f for f in all_flags if f.id == flag_id]
    if not matching_flags:
        raise ValueError(f"Failed to load updated RiskFlag '{flag_id}'")
    return matching_flags[0]
