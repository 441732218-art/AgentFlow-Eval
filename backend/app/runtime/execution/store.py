# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution lifecycle store for Runtime service queries."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.execution.models import ExecutionRecord, _utc_now


class ExecutionStore(ABC):
    """Persist execution status, results, and trace references."""

    @abstractmethod
    def save(self, record: ExecutionRecord) -> None:
        """Create or replace an execution record."""

    @abstractmethod
    def get(self, execution_id: str) -> ExecutionRecord | None:
        """Return a record by execution id."""

    @abstractmethod
    def update_status(self, execution_id: str, status: str) -> None:
        """Update lifecycle status for an existing record."""


class InMemoryExecutionStore(ExecutionStore):
    """Dict-backed execution store for tests and default in-process runs."""

    def __init__(self) -> None:
        self._records: dict[str, ExecutionRecord] = {}

    def save(self, record: ExecutionRecord) -> None:
        existing = self._records.get(record.execution_id)
        if existing is not None:
            record.created_at = existing.created_at
        record.updated_at = _utc_now()
        self._records[record.execution_id] = record

    def get(self, execution_id: str) -> ExecutionRecord | None:
        return self._records.get(execution_id)

    def update_status(self, execution_id: str, status: str) -> None:
        record = self._records.get(execution_id)
        if record is None:
            raise KeyError(f"Execution not found: {execution_id}")
        record.status = status
        record.updated_at = _utc_now()
