# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory execution state store."""

from __future__ import annotations

import threading

from app.runtime.state.models import ExecutionState


class InMemoryExecutionStateStore:
    """Thread-safe dict-backed execution state store."""

    def __init__(self) -> None:
        self._states: dict[str, ExecutionState] = {}
        self._lock = threading.Lock()

    def create(self, state: ExecutionState) -> None:
        with self._lock:
            if state.execution_id in self._states:
                raise KeyError(f"Execution state already exists: {state.execution_id}")
            self._states[state.execution_id] = state

    def get(self, execution_id: str) -> ExecutionState | None:
        with self._lock:
            return self._states.get(execution_id)

    def update(self, state: ExecutionState) -> None:
        with self._lock:
            if state.execution_id not in self._states:
                raise KeyError(f"Execution state not found: {state.execution_id}")
            self._states[state.execution_id] = state

    def delete(self, execution_id: str) -> None:
        with self._lock:
            self._states.pop(execution_id, None)
