from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from ledgersense.db.models import AuditEventRecord, RunRecord
from ledgersense.domain.models import ALLOWED_TRANSITIONS, RunStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted on a Run."""


def transition_run_status(
    run_id: str,
    new_status: RunStatus,
    session: Session,
    actor: str = "system",
    reason: str | None = None,
) -> RunRecord:
    """Validate and execute a run state transition, appending an AuditEvent."""
    run = session.get(RunRecord, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    current_status = run.status
    allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_next:
        raise InvalidStateTransitionError(
            f"Illegal state transition from {current_status} to {new_status}. Allowed: {sorted(allowed_next)}"
        )

    run.status = new_status
    session.add(run)

    now = datetime.now(UTC)
    desc = reason or f"State transition from {current_status} to {new_status}"
    payload_hash = hashlib.sha256(
        f"{current_status}->{new_status}:{run_id}".encode()
    ).hexdigest()

    audit_event = AuditEventRecord(
        id=f"evt:{uuid.uuid4().hex[:12]}",
        ts=now,
        run_id=run_id,
        actor=actor,
        action="STATE_CHANGE",
        entity_id=run_id,
        reason=desc,
        payload_hash=payload_hash,
    )
    session.add(audit_event)
    session.commit()
    session.refresh(run)

    return run
