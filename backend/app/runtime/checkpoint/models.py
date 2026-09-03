# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution checkpoint models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.runtime.state.models import ExecutionState


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Checkpoint:
    """Immutable durable recovery point for an agent execution."""

    checkpoint_id: str
    execution_id: str
    plan_id: str | None = None
    step_id: str | None = None
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_execution_state(
        cls,
        *,
        checkpoint_id: str,
        state: ExecutionState,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Build a checkpoint snapshot from the current execution state."""
        snapshot = {
            "agent_id": state.agent_id,
            "plan_id": state.plan_id,
            "status": state.status,
            "current_step": state.current_step,
            "task": state.metadata.get("task"),
            "completed_steps": list(state.metadata.get("completed_steps", [])),
        }
        return cls(
            checkpoint_id=checkpoint_id,
            execution_id=state.execution_id,
            plan_id=state.plan_id,
            step_id=step_id,
            state_snapshot=snapshot,
            metadata=dict(metadata or {}),
        )
