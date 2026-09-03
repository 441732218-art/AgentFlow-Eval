# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime memory context store."""

from __future__ import annotations

import threading

from app.runtime.context_memory.models import MemoryContext


class InMemoryMemoryStore:
    """Thread-safe dict-backed runtime memory store."""

    def __init__(self) -> None:
        self._contexts: dict[str, MemoryContext] = {}
        self._lock = threading.Lock()

    def create(self, context: MemoryContext) -> None:
        with self._lock:
            if context.memory_id in self._contexts:
                raise KeyError(f"Memory context already exists: {context.memory_id}")
            self._contexts[context.memory_id] = context

    def get(self, memory_id: str) -> MemoryContext | None:
        with self._lock:
            return self._contexts.get(memory_id)

    def update(self, context: MemoryContext) -> None:
        with self._lock:
            if context.memory_id not in self._contexts:
                raise KeyError(f"Memory context not found: {context.memory_id}")
            self._contexts[context.memory_id] = context

    def delete(self, memory_id: str) -> None:
        with self._lock:
            self._contexts.pop(memory_id, None)

    def list(
        self,
        *,
        execution_id: str | None = None,
        agent_id: str | None = None,
        namespace: str | None = None,
    ) -> list[MemoryContext]:
        with self._lock:
            records = list(self._contexts.values())
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        if agent_id is not None:
            records = [record for record in records if record.agent_id == agent_id]
        if namespace is not None:
            records = [record for record in records if record.namespace == namespace]
        return sorted(records, key=lambda record: record.created_at)
