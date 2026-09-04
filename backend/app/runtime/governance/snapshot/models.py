# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance evaluation snapshot models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernanceBindingSnapshotType = Literal["policy", "runtime"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernanceBindingSnapshot:
    """Immutable summary of one governance binding artifact."""

    binding_id: str
    binding_type: GovernanceBindingSnapshotType
    status: str
    applied: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceBindingSnapshot:
        """Return a new binding snapshot with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceSnapshot:
    """Immutable governance evaluation snapshot for one execution."""

    snapshot_id: str
    execution_id: str
    policy_versions: tuple[str, ...] = ()
    configuration_id: str | None = None
    decision_id: str | None = None
    enforcement_status: str | None = None
    binding_results: tuple[GovernanceBindingSnapshot, ...] = ()
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceSnapshot:
        """Return a new governance snapshot with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        if "policy_versions" in changes:
            changes["policy_versions"] = tuple(changes["policy_versions"])
        if "binding_results" in changes:
            changes["binding_results"] = tuple(changes["binding_results"])
        return replace(self, **changes)
