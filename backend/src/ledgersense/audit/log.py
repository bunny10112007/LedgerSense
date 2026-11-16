from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlmodel import Session

from ledgersense.db.repository import Repository
from ledgersense.db.session import engine
from ledgersense.domain.models import AuditEvent


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of a payload dictionary using canonical JSON."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def append(event: AuditEvent, session: Session | None = None) -> AuditEvent:
    """Append an immutable audit event to the append-only audit trail."""
    if session is not None:
        repo = Repository(session)
        repo.append_audit_event(event)
    else:
        with Session(engine) as s:
            repo = Repository(s)
            repo.append_audit_event(event)
    return event


def get_events(run_id: str, session: Session | None = None) -> list[AuditEvent]:
    """Retrieve the chronological audit trail for a reconciliation run."""
    if session is not None:
        repo = Repository(session)
        records = repo.get_audit_events(run_id)
    else:
        with Session(engine) as s:
            repo = Repository(s)
            records = repo.get_audit_events(run_id)

    return [
        AuditEvent(
            id=r.id,
            ts=r.ts,
            run_id=r.run_id,
            actor=r.actor,
            action=r.action,
            entity_id=r.entity_id,
            reason=r.reason,
            payload_hash=r.payload_hash,
        )
        for r in records
    ]


def update(*args: Any, **kwargs: Any) -> None:
    """Explicitly forbidden on append-only audit log."""
    raise NotImplementedError("audit_events is append-only: UPDATE is forbidden")


def delete(*args: Any, **kwargs: Any) -> None:
    """Explicitly forbidden on append-only audit log."""
    raise NotImplementedError("audit_events is append-only: DELETE is forbidden")
