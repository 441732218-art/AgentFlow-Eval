# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance decision routing models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

GovernanceRouteType = Literal["ALLOW", "WARNING", "APPROVAL", "BLOCK", "UNKNOWN"]
GovernanceRouteAction = Literal[
    "CONTINUE",
    "CONTINUE_WITH_WARNING",
    "WAIT_APPROVAL",
    "BLOCK",
    "NO_ACTION",
]


@dataclass(frozen=True)
class GovernanceRouteRequest:
    """Normalized governance decision routing input."""

    execution_id: str
    decision_status: str
    enforcement_status: str | None = None
    policy_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceRouteRequest:
        """Return a new route request with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceRouteResult:
    """Immutable governance decision routing result."""

    route_id: str
    execution_id: str
    route_type: GovernanceRouteType
    action: GovernanceRouteAction
    approval_required: bool
    blocked: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceRouteResult:
        """Return a new route result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
