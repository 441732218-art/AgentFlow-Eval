# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance enforcement models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

from app.runtime.governance.models import GovernanceDecisionStatus

GovernanceActionType = Literal["ALLOW", "WARN", "BLOCK"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceAction:
    """Immutable enforcement action derived from a governance decision."""

    action_id: str
    execution_id: str
    decision_status: GovernanceDecisionStatus
    action_type: GovernanceActionType
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceAction:
        """Return a new action with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
