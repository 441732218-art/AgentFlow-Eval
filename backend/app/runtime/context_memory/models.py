# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime memory context models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class MemoryContext:
    """Immutable runtime memory context for agent pipeline executions."""

    memory_id: str
    execution_id: str
    agent_id: str
    namespace: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def with_updates(self, **changes: Any) -> MemoryContext:
        """Return a new memory context with updated fields and a fresh ``updated_at``."""
        if "updated_at" not in changes:
            changes["updated_at"] = _utc_now()
        if "data" in changes:
            changes["data"] = dict(changes["data"])
        return replace(self, **changes)
