# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance evidence correlation models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernanceEvidenceReferenceType = Literal["evidence", "decision", "snapshot"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceEvidenceReference:
    """Immutable reference to one governance evidence artifact."""

    reference_id: str
    reference_type: GovernanceEvidenceReferenceType
    execution_id: str
    artifact_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceEvidenceReference:
        """Return a new evidence reference with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class EvidenceCorrelation:
    """Immutable correlation between execution evidence and governance artifacts."""

    correlation_id: str
    execution_id: str
    evidence_id: str | None = None
    decision_id: str | None = None
    snapshot_id: str | None = None
    references: tuple[GovernanceEvidenceReference, ...] = ()
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> EvidenceCorrelation:
        """Return a new evidence correlation with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        if "references" in changes:
            changes["references"] = tuple(changes["references"])
        return replace(self, **changes)
