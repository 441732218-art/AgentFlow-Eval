# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Checkpoint store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.checkpoint.models import Checkpoint


class CheckpointStore(Protocol):
    """Persists execution checkpoints for durable recovery."""

    def save(self, checkpoint: Checkpoint) -> None:
        """Persist a checkpoint record."""

    def get(self, checkpoint_id: str) -> Checkpoint | None:
        """Return a checkpoint by id."""

    def get_latest(self, execution_id: str) -> Checkpoint | None:
        """Return the most recent checkpoint for an execution."""

    def list_by_execution(self, execution_id: str) -> list[Checkpoint]:
        """Return checkpoints for an execution ordered by creation time."""

    def delete(self, checkpoint_id: str) -> None:
        """Remove a checkpoint by id."""
