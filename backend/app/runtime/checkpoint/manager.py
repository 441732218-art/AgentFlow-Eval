# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Checkpoint manager for durable execution recovery."""

from __future__ import annotations

import uuid
from typing import Any

from app.runtime.checkpoint.models import Checkpoint
from app.runtime.checkpoint.store import CheckpointStore
from app.runtime.planning.models import ExecutionPlan
from app.runtime.state.models import ExecutionState


class CheckpointManager:
    """Coordinates checkpoint persistence and resume preparation."""

    def __init__(self, store: CheckpointStore) -> None:
        self._store = store

    def save_checkpoint(
        self,
        *,
        execution_id: str,
        plan_id: str | None = None,
        step_id: str | None = None,
        state_snapshot: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=uuid.uuid4().hex,
            execution_id=execution_id,
            plan_id=plan_id,
            step_id=step_id,
            state_snapshot=dict(state_snapshot or {}),
            metadata=dict(metadata or {}),
        )
        self._store.save(checkpoint)
        return checkpoint

    def save_from_state(
        self,
        state: ExecutionState,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        checkpoint = Checkpoint.from_execution_state(
            checkpoint_id=uuid.uuid4().hex,
            state=state,
            step_id=step_id,
            metadata=metadata,
        )
        self._store.save(checkpoint)
        return checkpoint

    def get_resume_point(self, execution_id: str) -> Checkpoint | None:
        """Return the latest checkpoint usable as a resume point."""
        return self._store.get_latest(execution_id)

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        return self._store.get(checkpoint_id)

    def plan_for_resume(
        self,
        plan: ExecutionPlan,
        checkpoint: Checkpoint,
    ) -> ExecutionPlan:
        """Return a plan containing only steps that remain after a checkpoint."""
        completed_steps = set(checkpoint.state_snapshot.get("completed_steps", []))
        remaining_steps = tuple(
            step for step in plan.steps if step.name not in completed_steps
        )
        return ExecutionPlan(
            plan_id=plan.plan_id,
            agent_id=plan.agent_id,
            steps=remaining_steps,
            metadata=dict(plan.metadata),
        )
