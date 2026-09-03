# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime memory context lifecycle manager."""

from __future__ import annotations

import uuid
from typing import Any

from app.runtime.context_memory.models import MemoryContext
from app.runtime.context_memory.store import MemoryStore


class MemoryContextManager:
    """Loads, updates, and persists runtime memory contexts for pipeline runs."""

    def __init__(self, store: MemoryStore, *, namespace: str = "default") -> None:
        self._store = store
        self._namespace = namespace
        self._active: MemoryContext | None = None

    def load_context(
        self,
        *,
        execution_id: str,
        agent_id: str,
        namespace: str | None = None,
    ) -> MemoryContext:
        """Load an existing memory context or create a new one for the execution."""
        resolved_namespace = namespace or self._namespace
        existing_records = self._store.list(
            execution_id=execution_id,
            agent_id=agent_id,
            namespace=resolved_namespace,
        )
        if existing_records:
            context = existing_records[-1]
            self._active = context
            return context

        context = MemoryContext(
            memory_id=uuid.uuid4().hex,
            execution_id=execution_id,
            agent_id=agent_id,
            namespace=resolved_namespace,
            data={},
        )
        self._store.create(context)
        self._active = context
        return context

    def update_context(
        self,
        context: MemoryContext,
        updates: dict[str, Any],
    ) -> MemoryContext:
        """Merge runtime updates into the active memory context."""
        updated = context.with_updates(data={**context.data, **updates})
        self._active = updated
        return updated

    def persist_context(self, context: MemoryContext | None = None) -> MemoryContext:
        """Persist the active or supplied memory context to the store."""
        target = context or self._active
        if target is None:
            raise RuntimeError("no memory context to persist")

        existing = self._store.get(target.memory_id)
        if existing is None:
            self._store.create(target)
        else:
            self._store.update(target)
        self._active = target
        return target
