# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Policy execution binding models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

PolicyBindingStatus = Literal["BOUND", "NOT_FOUND", "DISABLED"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PolicyBindingRequest:
    """Immutable policy execution binding request."""

    policy_id: str
    policy_version: str
    execution_id: str
    agent_id: str
    runtime_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> PolicyBindingRequest:
        """Return a new policy binding request with updated fields."""
        if "runtime_context" in changes:
            changes["runtime_context"] = dict(changes["runtime_context"])
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class PolicyBindingResult:
    """Immutable policy execution binding result."""

    binding_id: str
    policy_id: str
    policy_version: str
    execution_id: str
    status: PolicyBindingStatus
    applied: bool
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> PolicyBindingResult:
        """Return a new policy binding result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
