# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance decision gateway models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

from app.runtime.governance.control.models import GovernanceControlDecision

GovernanceGateStatus = Literal["ALLOW", "WARN", "REQUIRE_APPROVAL", "BLOCK"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceGateRequest:
    """Immutable gateway evaluation request."""

    execution_id: str
    agent_id: str
    tool_name: str
    decision_id: str
    control_decision: GovernanceControlDecision
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceGateRequest:
        """Return a new gate request with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceGateResult:
    """Immutable gateway evaluation result."""

    gate_id: str
    execution_id: str
    status: GovernanceGateStatus
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceGateResult:
        """Return a new gate result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
