# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime orchestrator models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

GovernanceOrchestratorRouteType = Literal[
    "ALLOW",
    "WARNING",
    "APPROVAL",
    "BLOCK",
    "UNKNOWN",
]
GovernanceOrchestratorAction = Literal[
    "CONTINUE",
    "CONTINUE_WITH_WARNING",
    "WAIT_APPROVAL",
    "BLOCK",
    "NO_ACTION",
]


@dataclass(frozen=True)
class GovernanceExecutionRequest:
    """Normalized governance orchestration input."""

    execution_id: str
    decision_status: str
    enforcement_status: str | None = None
    policy_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceExecutionRequest:
        """Return a new orchestration request with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceExecutionResult:
    """Immutable governance orchestration result."""

    execution_id: str
    route_type: GovernanceOrchestratorRouteType
    action: GovernanceOrchestratorAction
    enforcement_applied: bool
    approval_required: bool
    blocked: bool
    report_generated: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceExecutionResult:
        """Return a new orchestration result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
