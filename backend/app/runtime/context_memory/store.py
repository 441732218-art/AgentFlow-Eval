# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime memory context store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.context_memory.models import MemoryContext


class MemoryStore(Protocol):
    """Persists runtime memory contexts for agent executions."""

    def create(self, context: MemoryContext) -> None:
        """Create a new memory context record."""

    def get(self, memory_id: str) -> MemoryContext | None:
        """Return a memory context by id."""

    def update(self, context: MemoryContext) -> None:
        """Replace an existing memory context record."""

    def delete(self, memory_id: str) -> None:
        """Remove a memory context by id."""

    def list(
        self,
        *,
        execution_id: str | None = None,
        agent_id: str | None = None,
        namespace: str | None = None,
    ) -> list[MemoryContext]:
        """List memory contexts with optional filters."""
