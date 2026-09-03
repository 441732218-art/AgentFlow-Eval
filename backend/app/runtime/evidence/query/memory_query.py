# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime evidence query service."""

from __future__ import annotations

from app.runtime.evidence.memory_store import InMemoryEvidenceStore
from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.evidence.query.models import EvidenceQuery
from app.runtime.evidence.query.query import EvidenceQueryService, filter_evidence


class InMemoryEvidenceQueryService(EvidenceQueryService):
    """Read-only evidence query service for in-memory stores."""

    def __init__(self, store: InMemoryEvidenceStore) -> None:
        super().__init__(store)
        self._memory_store = store

    def query(self, query: EvidenceQuery) -> list[ExecutionEvidence]:
        """Return evidence records matching the query criteria."""
        records = self._load_records(query)
        return filter_evidence(records, query)

    def _load_records(self, query: EvidenceQuery) -> list[ExecutionEvidence]:
        if query.execution_id is not None:
            record = self._memory_store.get_by_execution(query.execution_id)
            return [record] if record is not None else []
        if query.agent_id is not None:
            return self._memory_store.list_by_agent(query.agent_id)
        return self._memory_store.list_all()
