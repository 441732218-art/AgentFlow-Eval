# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance lifecycle orchestration models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.approval.models import ApprovalDecision
from app.runtime.governance.enforcement.models import GovernanceAction
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.reporting.models import GovernanceReport


@dataclass(frozen=True)
class GovernanceLifecycleContext:
    """Immutable governance lifecycle state for one execution."""

    execution_id: str
    evidence: ExecutionEvidence | None = None
    decision: GovernanceDecision | None = None
    action: GovernanceAction | None = None
    approval: ApprovalDecision | None = None
    report: GovernanceReport | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceLifecycleContext:
        """Return a new lifecycle context with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceLifecycleResult:
    """Immutable result produced by governance lifecycle orchestration."""

    execution_id: str
    final_status: str
    decision_status: str | None = None
    action_type: str | None = None
    approval_status: str | None = None
    report_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceLifecycleResult:
        """Return a new lifecycle result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
