# AgentFlow Intelligence v2.0 — Runtime evidence query tests (Phase 11.5)

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.runtime.audit.models import AuditRecord
from app.runtime.evidence.memory_store import InMemoryEvidenceStore
from app.runtime.evidence.models import EventSummary, ExecutionEvidence, PermissionDecision
from app.runtime.evidence.query.memory_query import InMemoryEvidenceQueryService
from app.runtime.evidence.query.models import EvidenceQuery
from app.runtime.evidence.query.query import EvidenceQueryService

_BASE_TIME = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)


def _audit_record(
    *,
    audit_id: str,
    event_type: str,
    execution_id: str,
    decision: str = "ALLOW",
) -> AuditRecord:
    return AuditRecord(
        audit_id=audit_id,
        event_type=event_type,
        execution_id=execution_id,
        agent_id="agent-query-1",
        correlation_id="corr-query-1",
        actor="agent-query-1",
        action=event_type,
        resource="execution",
        decision=decision,  # type: ignore[arg-type]
        severity="INFO",
    )


def _evidence(
    *,
    evidence_id: str,
    execution_id: str,
    agent_id: str = "agent-query-1",
    correlation_id: str | None = "corr-query-1",
    status: str = "COMPLETED",
    created_at: datetime = _BASE_TIME,
    audit_records: tuple[AuditRecord, ...] = (),
    permission_decisions: tuple[PermissionDecision, ...] = (),
    event_summary: EventSummary | None = None,
) -> ExecutionEvidence:
    return ExecutionEvidence(
        evidence_id=evidence_id,
        execution_id=execution_id,
        agent_id=agent_id,
        correlation_id=correlation_id,
        status=status,  # type: ignore[arg-type]
        audit_records=audit_records,
        permission_decisions=permission_decisions,
        event_summary=event_summary,
        created_at=created_at,
    )


def _seed_store() -> InMemoryEvidenceStore:
    store = InMemoryEvidenceStore()
    store.save(
        _evidence(
            evidence_id="evidence-1",
            execution_id="exec-query-1",
            created_at=_BASE_TIME,
            audit_records=(
                _audit_record(
                    audit_id="audit-1",
                    event_type="execution.start",
                    execution_id="exec-query-1",
                ),
            ),
            event_summary=EventSummary(
                total_events=1,
                event_types=("execution.start",),
            ),
        )
    )
    store.save(
        _evidence(
            evidence_id="evidence-2",
            execution_id="exec-query-2",
            agent_id="agent-query-2",
            correlation_id="corr-query-2",
            created_at=_BASE_TIME + timedelta(minutes=5),
            audit_records=(
                _audit_record(
                    audit_id="audit-2",
                    event_type="tool.permission.denied",
                    execution_id="exec-query-2",
                    decision="DENY",
                ),
            ),
            permission_decisions=(
                PermissionDecision(
                    execution_id="exec-query-2",
                    decision="DENY",
                    tool_name="email.send",
                    permission="email.send",
                ),
            ),
        )
    )
    store.save(
        _evidence(
            evidence_id="evidence-3",
            execution_id="exec-query-3",
            created_at=_BASE_TIME + timedelta(minutes=10),
            status="FAILED",
        )
    )
    return store


def test_query_by_execution_id() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    results = service.query(EvidenceQuery(execution_id="exec-query-1"))

    assert len(results) == 1
    assert results[0].evidence_id == "evidence-1"


def test_query_by_agent_id() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    results = service.query(EvidenceQuery(agent_id="agent-query-1"))

    assert len(results) == 2
    assert {record.execution_id for record in results} == {
        "exec-query-1",
        "exec-query-3",
    }


def test_query_by_correlation_id() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    results = service.query(EvidenceQuery(correlation_id="corr-query-2"))

    assert len(results) == 1
    assert results[0].execution_id == "exec-query-2"


def test_query_permission_deny_evidence() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    results = service.query(EvidenceQuery(decision="DENY"))

    assert len(results) == 1
    assert results[0].execution_id == "exec-query-2"
    assert results[0].permission_decisions[0].decision == "DENY"


def test_query_time_range() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    results = service.query(
        EvidenceQuery(
            start_time=_BASE_TIME + timedelta(minutes=1),
            end_time=_BASE_TIME + timedelta(minutes=8),
        )
    )

    assert len(results) == 1
    assert results[0].execution_id == "exec-query-2"


def test_query_limit() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    results = service.query(EvidenceQuery(agent_id="agent-query-1", limit=1))

    assert len(results) == 1
    assert results[0].execution_id == "exec-query-1"


def test_query_empty_result() -> None:
    store = _seed_store()
    service = InMemoryEvidenceQueryService(store)

    assert service.query(EvidenceQuery(execution_id="exec-missing")) == []
    assert service.query(EvidenceQuery(agent_id="agent-missing")) == []


def test_evidence_query_is_immutable() -> None:
    query = EvidenceQuery(execution_id="exec-query-1", limit=5)

    with pytest.raises(FrozenInstanceError):
        query.limit = 10  # type: ignore[misc]

    updated = query.with_updates(limit=10)
    assert updated.limit == 10
    assert query.limit == 5


def test_protocol_query_service_scopes_to_store_capabilities() -> None:
    store = _seed_store()
    service = EvidenceQueryService(store)

    by_agent = service.query(EvidenceQuery(agent_id="agent-query-1"))
    by_execution = service.query(EvidenceQuery(execution_id="exec-query-1"))
    unscoped = service.query(EvidenceQuery(correlation_id="corr-query-2"))

    assert len(by_agent) == 2
    assert len(by_execution) == 1
    assert unscoped == []
