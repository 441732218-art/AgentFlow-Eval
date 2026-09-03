# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance reporting models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernanceRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceReport:
    """Immutable governance report aggregated from runtime artifacts."""

    report_id: str
    execution_id: str
    risk_level: GovernanceRiskLevel
    decision_status: str
    summary: str
    evidence_count: int
    agent_id: str | None = None
    approval_status: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceReport:
        """Return a new report with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
