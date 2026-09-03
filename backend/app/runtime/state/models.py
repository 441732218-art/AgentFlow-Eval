# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime execution state models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

ExecutionStateStatus = Literal["RUNNING", "COMPLETED", "FAILED"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ExecutionState:
    """Immutable in-process execution state for agent pipeline runs."""

    execution_id: str
    agent_id: str
    plan_id: str
    status: ExecutionStateStatus
    current_step: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def with_updates(self, **changes: Any) -> ExecutionState:
        """Return a new state with updated fields and a fresh ``updated_at``."""
        if "updated_at" not in changes:
            changes["updated_at"] = _utc_now()
        return replace(self, **changes)
