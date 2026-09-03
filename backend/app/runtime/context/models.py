# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Unified runtime context aggregation models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.runtime.checkpoint.models import Checkpoint
    from app.runtime.context_memory.models import MemoryContext
    from app.runtime.state.models import ExecutionState


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable aggregated runtime context for agent pipeline executions."""

    execution_id: str
    agent_id: str
    state: ExecutionState | None = None
    checkpoint: Checkpoint | None = None
    memory: MemoryContext | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def with_updates(self, **changes: Any) -> RuntimeContext:
        """Return a new aggregated runtime context with a fresh ``updated_at``."""
        if "updated_at" not in changes:
            changes["updated_at"] = _utc_now()
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
