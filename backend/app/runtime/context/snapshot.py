# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Lightweight runtime context snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.runtime.context.models import RuntimeContext


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RuntimeContextSnapshot:
    """Lightweight observation and recovery snapshot for a runtime context."""

    execution_id: str
    status: str
    current_step: str | None = None
    latest_checkpoint_id: str | None = None
    memory_namespace: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_utc_now)


def build_snapshot(context: RuntimeContext) -> RuntimeContextSnapshot:
    """Build a snapshot from an aggregated runtime context."""
    state = context.state
    status = state.status if state is not None else str(context.metadata.get("status", "UNKNOWN"))
    current_step = state.current_step if state is not None else None
    latest_checkpoint_id = (
        context.checkpoint.checkpoint_id if context.checkpoint is not None else None
    )
    memory_namespace = context.memory.namespace if context.memory is not None else None
    return RuntimeContextSnapshot(
        execution_id=context.execution_id,
        status=status,
        current_step=current_step,
        latest_checkpoint_id=latest_checkpoint_id,
        memory_namespace=memory_namespace,
        metadata=dict(context.metadata),
    )
