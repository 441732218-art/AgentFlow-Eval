# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime evidence store."""

from __future__ import annotations

import threading

from app.runtime.evidence.models import ExecutionEvidence


class InMemoryEvidenceStore:
    """Thread-safe in-memory evidence store."""

    def __init__(self) -> None:
        self._records: dict[str, ExecutionEvidence] = {}
        self._lock = threading.Lock()

    def save(self, evidence: ExecutionEvidence) -> None:
        with self._lock:
            self._records[evidence.evidence_id] = evidence

    def get(self, evidence_id: str) -> ExecutionEvidence | None:
        with self._lock:
            return self._records.get(evidence_id)

    def get_by_execution(self, execution_id: str) -> ExecutionEvidence | None:
        with self._lock:
            matches = [
                record
                for record in self._records.values()
                if record.execution_id == execution_id
            ]
        if not matches:
            return None
        return max(matches, key=lambda record: record.created_at)

    def list_by_agent(self, agent_id: str) -> list[ExecutionEvidence]:
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.agent_id == agent_id
            ]
        return sorted(records, key=lambda record: record.created_at)

    def list_all(self) -> list[ExecutionEvidence]:
        """Return all stored evidence records sorted by creation time."""
        with self._lock:
            records = list(self._records.values())
        return sorted(records, key=lambda record: record.created_at)

    def delete(self, evidence_id: str) -> None:
        with self._lock:
            self._records.pop(evidence_id, None)
