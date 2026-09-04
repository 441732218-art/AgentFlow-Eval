# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime decision adapter models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

from app.runtime.governance.execution.models import GovernanceExecutionEffect
from app.runtime.governance.resolver.models import GovernanceEffectResolutionType

GovernanceRuntimeDecisionStatus = Literal[
    "ALLOW",
    "WARN",
    "DENY",
    "BLOCK",
    "REQUIRE_APPROVAL",
]


@dataclass(frozen=True)
class GovernanceRuntimeDecisionRequest:
    """Normalized governance decision adaptation input."""

    decision_id: str
    execution_id: str
    decision_status: GovernanceRuntimeDecisionStatus
    target: str
    reason: str
    agent_id: str | None = None
    evidence_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceRuntimeDecisionRequest:
        """Return a new adaptation request with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceRuntimeDecisionResult:
    """Immutable result of adapting a governance decision to runtime semantics."""

    result_id: str
    decision_id: str
    execution_id: str
    effect: GovernanceExecutionEffect
    effect_action_type: str
    resolution_type: GovernanceEffectResolutionType
    executable: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceRuntimeDecisionResult:
        """Return a new adaptation result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
