# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance control models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernanceControlDecisionStatus = Literal["ALLOW", "WARN", "REQUIRE_APPROVAL", "BLOCK"]
GovernanceControlActionType = Literal["ALLOW", "WARN", "REQUIRE_APPROVAL", "BLOCK"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceControlDecision:
    """Immutable control decision derived from a governance decision."""

    control_id: str
    execution_id: str
    decision_status: GovernanceControlDecisionStatus
    action_type: GovernanceControlActionType
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceControlDecision:
        """Return a new control decision with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
