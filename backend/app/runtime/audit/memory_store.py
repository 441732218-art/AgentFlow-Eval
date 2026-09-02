# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory audit store for tests and local governance queries."""

from __future__ import annotations

import threading

from app.runtime.audit.models import AuditRecord


class InMemoryAuditStore:
    """Thread-safe in-memory audit store."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._lock = threading.Lock()

    def append(self, record: AuditRecord) -> None:
        with self._lock:
            self._records.append(record)

    def query(
        self,
        execution_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[AuditRecord]:
        with self._lock:
            records = list(self._records)
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        if tenant_id is not None:
            records = [record for record in records if record.tenant_id == tenant_id]
        return records

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
