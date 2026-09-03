# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime evidence read-only query service."""

from __future__ import annotations

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.evidence.query.models import EvidenceQuery
from app.runtime.evidence.store import EvidenceStore


def filter_evidence(
    records: list[ExecutionEvidence],
    query: EvidenceQuery,
) -> list[ExecutionEvidence]:
    """Apply query filters to evidence records without mutating them."""
    filtered = list(records)

    if query.execution_id is not None:
        filtered = [
            record for record in filtered if record.execution_id == query.execution_id
        ]
    if query.agent_id is not None:
        filtered = [record for record in filtered if record.agent_id == query.agent_id]
    if query.correlation_id is not None:
        filtered = [
            record
            for record in filtered
            if record.correlation_id == query.correlation_id
        ]
    if query.decision is not None:
        filtered = [
            record
            for record in filtered
            if _matches_decision(record, query.decision)
        ]
    if query.event_type is not None:
        filtered = [
            record
            for record in filtered
            if _matches_event_type(record, query.event_type)
        ]
    if query.start_time is not None:
        filtered = [
            record for record in filtered if record.created_at >= query.start_time
        ]
    if query.end_time is not None:
        filtered = [
            record for record in filtered if record.created_at <= query.end_time
        ]

    filtered.sort(key=lambda record: record.created_at)

    if query.limit is not None:
        filtered = filtered[: query.limit]

    return filtered


def _matches_decision(record: ExecutionEvidence, decision: str) -> bool:
    if any(item.decision == decision for item in record.permission_decisions):
        return True
    return any(audit.decision == decision for audit in record.audit_records)


def _matches_event_type(record: ExecutionEvidence, event_type: str) -> bool:
    if record.event_summary is not None and event_type in record.event_summary.event_types:
        return True
    return any(audit.event_type == event_type for audit in record.audit_records)


class EvidenceQueryService:
    """Read-only evidence query service backed by an evidence store."""

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    @property
    def store(self) -> EvidenceStore:
        return self._store

    def query(self, query: EvidenceQuery) -> list[ExecutionEvidence]:
        """Return evidence records matching the query criteria."""
        records = self._load_records(query)
        return filter_evidence(records, query)

    def _load_records(self, query: EvidenceQuery) -> list[ExecutionEvidence]:
        if query.execution_id is not None:
            record = self._store.get_by_execution(query.execution_id)
            return [record] if record is not None else []
        if query.agent_id is not None:
            return self._store.list_by_agent(query.agent_id)
        return []
