# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime enforcement pipeline models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

from app.runtime.governance.gateway.models import GovernanceGateResult

EnforcementStatus = Literal["ALLOW", "WARN", "BLOCK", "PENDING_APPROVAL"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class EnforcementRequest:
    """Immutable enforcement pipeline evaluation request."""

    execution_id: str
    gate_result: GovernanceGateResult
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> EnforcementRequest:
        """Return a new enforcement request with updated fields."""
        if "context" in changes:
            changes["context"] = dict(changes["context"])
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class EnforcementResult:
    """Immutable enforcement pipeline evaluation result."""

    enforcement_id: str
    execution_id: str
    status: EnforcementStatus
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> EnforcementResult:
        """Return a new enforcement result with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
