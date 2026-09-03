# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime event stream envelope models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

EXECUTION_START = "execution.start"
EXECUTION_COMPLETE = "execution.complete"
EXECUTION_FAILED = "execution.failed"
STEP_START = "step.start"
STEP_COMPLETE = "step.complete"
STEP_FAILED = "step.failed"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RuntimeEventEnvelope:
    """Immutable envelope for runtime event stream distribution."""

    event_id: str
    event_type: str
    correlation_id: str
    parent_event_id: str | None
    execution_id: str
    timestamp: datetime = field(default_factory=_utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> RuntimeEventEnvelope:
        """Return a new envelope with updated fields."""
        if "payload" in changes:
            changes["payload"] = dict(changes["payload"])
        return replace(self, **changes)
