from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Session

from ledgersense.audit.log import compute_payload_hash
from ledgersense.db.repository import Repository
from ledgersense.domain.models import ALLOWED_TRANSITIONS, AuditEvent, Run, RunStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted on a Run."""


def can_transition(current: RunStatus, target: RunStatus) -> bool:
    """Return True if the state transition from current to target is allowed."""
    return target in ALLOWED_TRANSITIONS.get(current, set())


def transition_run(
    session: Session,
    run_id: str,
    target: RunStatus,
    actor: str = "system",
    reason: str | None = None,
) -> Run:
    """Validate and transition a Run to target status, recording an AuditEvent."""
    repo = Repository(session)
    run_record = repo.get_run(run_id)
    if not run_record:
        raise ValueError(f"Run '{run_id}' not found")

    current: RunStatus = run_record.status  # type: ignore[assignment]
    if current == target:
        domain_run = repo.get_domain_run(run_id)
        if not domain_run:
            raise ValueError(f"Run '{run_id}' not found")
        return domain_run

    if not can_transition(current, target):
        allowed = sorted(ALLOWED_TRANSITIONS.get(current, set()))
        raise InvalidStateTransitionError(
            f"Illegal state transition from '{current}' to '{target}'. "
            f"Allowed transitions: {allowed if allowed else 'None (terminal)'}"
        )

    repo.update_run_status(run_id, target)

    evt = AuditEvent(
        id=f"evt:{uuid4().hex[:12]}",
        ts=datetime.now(UTC),
        run_id=run_id,
        actor=actor,
        action="STATE_CHANGE",
        entity_id=run_id,
        reason=reason or f"Transitioned from {current} to {target}",
        payload_hash=compute_payload_hash(
            {"run_id": run_id, "from": current, "to": target}
        ),
    )
    repo.append_audit_event(evt)

    updated_run = repo.get_domain_run(run_id)
    if not updated_run:
        raise ValueError(f"Failed to load run '{run_id}' after transition")
    return updated_run


def transition_run_status(
    run_id: str,
    new_status: RunStatus,
    session: Session,
    actor: str = "system",
    reason: str | None = None,
) -> Run:
    """Convenience alias for transition_run matching Dev A signature."""
    return transition_run(
        session=session,
        run_id=run_id,
        target=new_status,
        actor=actor,
        reason=reason,
    )
