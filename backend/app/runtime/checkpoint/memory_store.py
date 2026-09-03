# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory checkpoint store."""

from __future__ import annotations

import threading

from app.runtime.checkpoint.models import Checkpoint


class InMemoryCheckpointStore:
    """Thread-safe dict-backed checkpoint store."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}
        self._lock = threading.Lock()

    def save(self, checkpoint: Checkpoint) -> None:
        with self._lock:
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    def get(self, checkpoint_id: str) -> Checkpoint | None:
        with self._lock:
            return self._checkpoints.get(checkpoint_id)

    def get_latest(self, execution_id: str) -> Checkpoint | None:
        checkpoints = self.list_by_execution(execution_id)
        if not checkpoints:
            return None
        return checkpoints[-1]

    def list_by_execution(self, execution_id: str) -> list[Checkpoint]:
        with self._lock:
            records = [
                checkpoint
                for checkpoint in self._checkpoints.values()
                if checkpoint.execution_id == execution_id
            ]
        return sorted(records, key=lambda checkpoint: checkpoint.created_at)

    def delete(self, checkpoint_id: str) -> None:
        with self._lock:
            self._checkpoints.pop(checkpoint_id, None)
