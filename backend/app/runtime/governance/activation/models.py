# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime activation models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class GovernanceActivationRequest:
    """Input for optional governance runtime activation."""

    execution_id: str
    runtime_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceActivationRequest:
        """Return a new activation request with updated fields."""
        if "runtime_context" in changes:
            changes["runtime_context"] = dict(changes["runtime_context"])
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceActivationResult:
    """Immutable result of a governance runtime activation decision."""

    execution_id: str
    activated: bool
    governance_enabled: bool
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceActivationResult:
        """Return a new activation result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
