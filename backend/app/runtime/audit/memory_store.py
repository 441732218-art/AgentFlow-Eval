# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime audit store."""

from __future__ import annotations

import threading

from app.runtime.audit.models import AuditRecord


class InMemoryAuditStore:
    """Thread-safe dict-backed audit store."""

    def __init__(self) -> None:
        self._records: dict[str, AuditRecord] = {}
        self._lock = threading.Lock()

    def record(self, record: AuditRecord) -> None:
        with self._lock:
            self._records[record.audit_id] = record

    def get(self, audit_id: str) -> AuditRecord | None:
        with self._lock:
            return self._records.get(audit_id)

    def list_by_execution(self, execution_id: str) -> list[AuditRecord]:
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.execution_id == execution_id
            ]
        return sorted(records, key=lambda record: record.timestamp)

    def list_by_agent(self, agent_id: str) -> list[AuditRecord]:
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.agent_id == agent_id
            ]
        return sorted(records, key=lambda record: record.timestamp)

    def delete(self, audit_id: str) -> None:
        with self._lock:
            self._records.pop(audit_id, None)

    def append(self, record: AuditRecord) -> None:
        self.record(record)

    def query(
        self,
        execution_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[AuditRecord]:
        with self._lock:
            records = list(self._records.values())
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        if tenant_id is not None:
            records = [record for record in records if record.tenant_id == tenant_id]
        return sorted(records, key=lambda record: record.timestamp)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
