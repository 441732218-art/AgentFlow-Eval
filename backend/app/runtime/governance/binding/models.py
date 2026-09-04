# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime enforcement binding models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

from app.runtime.governance.enforcement_pipeline.models import EnforcementResult

RuntimeBindingDecision = Literal["ALLOW", "WARN", "BLOCK", "PENDING_APPROVAL"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RuntimeBindingRequest:
    """Immutable runtime enforcement binding request."""

    execution_id: str
    enforcement_result: EnforcementResult
    runtime_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> RuntimeBindingRequest:
        """Return a new binding request with updated fields."""
        if "runtime_context" in changes:
            changes["runtime_context"] = dict(changes["runtime_context"])
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class RuntimeBindingResult:
    """Immutable runtime enforcement binding result."""

    binding_id: str
    execution_id: str
    decision: RuntimeBindingDecision
    applied: bool
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> RuntimeBindingResult:
        """Return a new binding result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
