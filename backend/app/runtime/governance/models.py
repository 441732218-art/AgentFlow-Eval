# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance decision models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernanceDecisionStatus = Literal["ALLOW", "WARN", "DENY"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceRule:
    """Immutable governance rule metadata."""

    rule_id: str
    name: str
    description: str
    enabled: bool = True

    def with_updates(self, **changes: Any) -> GovernanceRule:
        """Return a new rule definition with updated fields."""
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceDecision:
    """Immutable governance decision produced from execution evidence."""

    decision_id: str
    execution_id: str
    agent_id: str
    status: GovernanceDecisionStatus
    reasons: tuple[str, ...] = ()
    evaluated_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceDecision:
        """Return a new decision with updated fields."""
        if "reasons" in changes:
            changes["reasons"] = tuple(changes["reasons"])
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
