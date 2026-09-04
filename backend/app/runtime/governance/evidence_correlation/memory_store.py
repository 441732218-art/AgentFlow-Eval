# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance evidence correlation store."""

from __future__ import annotations

import threading

from app.runtime.governance.evidence_correlation.models import EvidenceCorrelation


class InMemoryEvidenceCorrelationStore:
    """Thread-safe in-memory governance evidence correlation store."""

    def __init__(self) -> None:
        self._correlations: dict[str, EvidenceCorrelation] = {}
        self._lock = threading.Lock()

    def save(self, correlation: EvidenceCorrelation) -> None:
        """Persist one evidence correlation record."""
        with self._lock:
            self._correlations[correlation.correlation_id] = correlation

    def get(self, correlation_id: str) -> EvidenceCorrelation | None:
        """Return one evidence correlation by identifier."""
        with self._lock:
            return self._correlations.get(correlation_id)

    def list_by_execution(self, execution_id: str) -> list[EvidenceCorrelation]:
        """Return correlations recorded for an execution."""
        with self._lock:
            records = [
                correlation
                for correlation in self._correlations.values()
                if correlation.execution_id == execution_id
            ]
        return sorted(records, key=lambda record: record.created_at)

    def list_all(self) -> list[EvidenceCorrelation]:
        """Return all stored evidence correlations."""
        with self._lock:
            records = list(self._correlations.values())
        return sorted(records, key=lambda record: record.created_at)

    def remove(self, correlation_id: str) -> None:
        """Remove one evidence correlation record."""
        with self._lock:
            self._correlations.pop(correlation_id, None)

    def clear(self) -> None:
        """Remove all stored evidence correlations."""
        with self._lock:
            self._correlations.clear()
