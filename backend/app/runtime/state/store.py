# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution state store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.state.models import ExecutionState


class ExecutionStateStore(Protocol):
    """Persists runtime execution state for in-process observability and recovery."""

    def create(self, state: ExecutionState) -> None:
        """Create a new execution state record."""

    def get(self, execution_id: str) -> ExecutionState | None:
        """Return execution state by id."""

    def update(self, state: ExecutionState) -> None:
        """Replace an existing execution state record."""

    def delete(self, execution_id: str) -> None:
        """Remove execution state by id."""
