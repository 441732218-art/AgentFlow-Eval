# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance execution contract models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernanceExecutionActionType = Literal["ALLOW", "WARN", "BLOCK", "REQUIRE_APPROVAL"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceExecutionEffect:
    """Immutable governance execution effect descriptor."""

    effect_id: str
    decision_id: str
    action_type: GovernanceExecutionActionType
    target: str
    reason: str
    evidence_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceExecutionEffect:
        """Return a new execution effect with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceExecutionRecord:
    """Immutable record of one observed governance execution effect."""

    effect_id: str
    decision_id: str
    action_type: GovernanceExecutionActionType
    target: str
    reason: str
    evidence_reference: str | None
    applied: bool
    executed_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceExecutionRecord:
        """Return a new execution record with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
