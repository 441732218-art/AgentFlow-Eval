# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime execution hook event models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

EXECUTION_STARTED = "execution.started"
EXECUTION_COMPLETED = "execution.completed"
EXECUTION_FAILED = "execution.failed"
STEP_STARTED = "step.started"
STEP_COMPLETED = "step.completed"
STEP_FAILED = "step.failed"
TOOL_STARTED = "tool.started"
TOOL_COMPLETED = "tool.completed"
TOOL_FAILED = "tool.failed"

RuntimeHookEventType = Literal[
    "execution.started",
    "execution.completed",
    "execution.failed",
    "step.started",
    "step.completed",
    "step.failed",
    "tool.started",
    "tool.completed",
    "tool.failed",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RuntimeHookEvent:
    """Immutable runtime lifecycle hook event."""

    event_id: str
    event_type: RuntimeHookEventType
    execution_id: str
    agent_id: str
    timestamp: datetime = field(default_factory=_utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> RuntimeHookEvent:
        """Return a new hook event with updated fields."""
        if "payload" in changes:
            changes["payload"] = dict(changes["payload"])
        return replace(self, **changes)
