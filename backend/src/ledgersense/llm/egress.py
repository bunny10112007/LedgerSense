from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from ledgersense.db.models import AuditEventRecord, EgressLogRecord
from ledgersense.db.session import engine


def log_outbound_call(
    file_hash: str,
    payload_bytes: bytes | int,
    model_id: str,
    masked: bool = False,
    run_id: str = "run:default",
    payload_raw: str | bytes | None = None,
    session: Session | None = None,
) -> tuple[EgressLogRecord, AuditEventRecord]:
    """Record an outbound LLM call in both egress_log and audit_events."""
    byte_count = len(payload_bytes) if isinstance(payload_bytes, bytes) else int(payload_bytes)

    if payload_raw is None:
        payload_data = f"{file_hash}:{model_id}:{byte_count}:{masked}".encode()
    elif isinstance(payload_raw, str):
        payload_data = payload_raw.encode()
    else:
        payload_data = payload_raw

    payload_hash = hashlib.sha256(payload_data).hexdigest()
    now = datetime.now(UTC)

    egress_record = EgressLogRecord(
        id=f"egress:{uuid.uuid4().hex[:16]}",
        ts=now,
        run_id=run_id,
        file_hash=file_hash,
        bytes=byte_count,
        model_id=model_id,
        masked=masked,
    )

    audit_record = AuditEventRecord(
        id=f"evt:{uuid.uuid4().hex[:12]}",
        ts=now,
        run_id=run_id,
        actor="system",
        action="LLM_CALL",
        entity_id=file_hash,
        reason=f"Outbound LLM call to {model_id} ({byte_count} bytes, masked={masked})",
        payload_hash=payload_hash,
    )

    if session is not None:
        session.add(egress_record)
        session.add(audit_record)
        session.commit()
        session.refresh(egress_record)
        session.refresh(audit_record)
    else:
        with Session(engine) as s:
            s.add(egress_record)
            s.add(audit_record)
            s.commit()
            s.refresh(egress_record)
            s.refresh(audit_record)

    return egress_record, audit_record
