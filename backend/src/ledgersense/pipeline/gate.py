from __future__ import annotations

import json

from sqlmodel import Session, select

from ledgersense.db.models import RiskFlagRecord
from ledgersense.domain.models import RiskFlag


def can_commit(run_id: str, session: Session) -> tuple[bool, list[RiskFlag]]:
    """Check if a run is cleared for commit.

    Returns (False, open_high_flags) if any HIGH severity risk flag remains OPEN.
    Otherwise returns (True, []).
    """
    statement = (
        select(RiskFlagRecord)
        .where(RiskFlagRecord.run_id == run_id)
        .where(RiskFlagRecord.severity == "HIGH")
        .where(RiskFlagRecord.status == "OPEN")
    )
    records = list(session.exec(statement).all())

    if not records:
        return True, []

    open_high_flags: list[RiskFlag] = []
    for r in records:
        entity_ids = json.loads(r.entity_ids_json) if r.entity_ids_json else []
        evidence = json.loads(r.evidence_json) if r.evidence_json else {}
        open_high_flags.append(
            RiskFlag(
                id=r.id,
                run_id=r.run_id,
                rule_id=r.rule_id,
                severity=r.severity,  # type: ignore[arg-type]
                entity_ids=entity_ids,
                legal_ref=r.legal_ref,
                evidence=evidence,
                suggested_action=r.suggested_action,
                status=r.status,  # type: ignore[arg-type]
                decided_by=r.decided_by,
                decision_reason=r.decision_reason,
                decided_at=r.decided_at,
            )
        )

    return False, open_high_flags
