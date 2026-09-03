# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Unified runtime context aggregation manager."""

from __future__ import annotations

from typing import Any

from app.runtime.checkpoint.models import Checkpoint
from app.runtime.context.models import RuntimeContext
from app.runtime.context.snapshot import RuntimeContextSnapshot, build_snapshot
from app.runtime.context_memory.models import MemoryContext
from app.runtime.state.models import ExecutionState


class RuntimeContextManager:
    """Aggregates execution state, checkpoint, and memory into one runtime context."""

    def __init__(self) -> None:
        self._contexts: dict[str, RuntimeContext] = {}

    def create_context(
        self,
        *,
        execution_id: str,
        agent_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeContext:
        context = RuntimeContext(
            execution_id=execution_id,
            agent_id=agent_id,
            metadata=dict(metadata or {}),
        )
        self._contexts[execution_id] = context
        return context

    def get_context(self, execution_id: str) -> RuntimeContext | None:
        return self._contexts.get(execution_id)

    def update_state(self, execution_id: str, state: ExecutionState) -> RuntimeContext:
        context = self._require_context(execution_id)
        updated = context.with_updates(state=state)
        self._contexts[execution_id] = updated
        return updated

    def update_checkpoint(
        self,
        execution_id: str,
        checkpoint: Checkpoint,
    ) -> RuntimeContext:
        context = self._require_context(execution_id)
        updated = context.with_updates(checkpoint=checkpoint)
        self._contexts[execution_id] = updated
        return updated

    def update_memory(self, execution_id: str, memory: MemoryContext) -> RuntimeContext:
        context = self._require_context(execution_id)
        updated = context.with_updates(memory=memory)
        self._contexts[execution_id] = updated
        return updated

    def snapshot(self, execution_id: str) -> RuntimeContextSnapshot:
        return build_snapshot(self._require_context(execution_id))

    def _require_context(self, execution_id: str) -> RuntimeContext:
        context = self._contexts.get(execution_id)
        if context is None:
            raise KeyError(f"Runtime context not found: {execution_id}")
        return context
