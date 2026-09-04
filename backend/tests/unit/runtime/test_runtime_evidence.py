# AgentFlow Intelligence v2.0 — Runtime evidence tests (Phase 11.4)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.analytics.collector import RuntimeAnalyticsCollector
from app.runtime.analytics.memory_store import InMemoryAnalyticsStore
from app.runtime.analytics.models import ExecutionMetric
from app.runtime.audit.memory_store import InMemoryAuditStore
from app.runtime.audit.models import AuditRecord
from app.runtime.audit.recorder import RuntimeAuditRecorder
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.checkpoint.memory_store import InMemoryCheckpointStore
from app.runtime.context.manager import RuntimeContextManager
from app.runtime.context.snapshot import RuntimeContextSnapshot
from app.runtime.context_memory.manager import MemoryContextManager
from app.runtime.context_memory.memory_store import InMemoryMemoryStore
from app.runtime.event_stream.memory_publisher import InMemoryEventPublisher
from app.runtime.event_stream.models import EXECUTION_START, RuntimeEventEnvelope
from app.runtime.evidence.collector import RuntimeEvidenceCollector
from app.runtime.evidence.memory_store import InMemoryEvidenceStore
from app.runtime.evidence.models import ExecutionEvidence, PermissionDecision
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.state.memory_store import InMemoryExecutionStateStore
from app.runtime.state.models import ExecutionState

_EVIDENCE_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "evidence"
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "app.core",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "trade_provider",
    "kafka",
    "redis",
    "ToolExecutionEngine",
    "PolicyEngine",
)


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-evidence-1",
        name="evidence-agent",
        tool_names=["probe.echo"],
    )


def _audit_record() -> AuditRecord:
    return AuditRecord(
        audit_id="audit-evidence-1",
        event_type="execution.start",
        execution_id="exec-evidence-1",
        agent_id="agent-evidence-1",
        correlation_id="corr-evidence-1",
        actor="agent-evidence-1",
        action="execution.start",
        resource="execution",
        decision="ALLOW",
        severity="INFO",
        metadata={"task": "evidence task"},
    )


def _execution_state() -> ExecutionState:
    return ExecutionState(
        execution_id="exec-evidence-1",
        agent_id="agent-evidence-1",
        plan_id="plan-evidence-1",
        status="COMPLETED",
        metadata={"task": "evidence task"},
    )


def _context_snapshot() -> RuntimeContextSnapshot:
    return RuntimeContextSnapshot(
        execution_id="exec-evidence-1",
        status="COMPLETED",
        latest_checkpoint_id="checkpoint-evidence-1",
        memory_namespace="memory-ns-1",
        metadata={"plan_id": "plan-evidence-1", "task": "evidence task"},
    )


def test_execution_evidence_is_immutable() -> None:
    evidence = ExecutionEvidence(
        evidence_id="evidence-1",
        execution_id="exec-evidence-1",
        agent_id="agent-evidence-1",
        correlation_id="corr-evidence-1",
        status="COMPLETED",
        audit_records=(_audit_record(),),
    )

    with pytest.raises(FrozenInstanceError):
        evidence.status = "FAILED"  # type: ignore[misc]

    updated = evidence.with_updates(status="FAILED")
    assert updated.status == "FAILED"
    assert evidence.status == "COMPLETED"


def test_evidence_store_crud() -> None:
    store = InMemoryEvidenceStore()
    evidence = ExecutionEvidence(
        evidence_id="evidence-crud-1",
        execution_id="exec-evidence-crud",
        agent_id="agent-evidence-1",
        correlation_id="corr-evidence-1",
        status="COMPLETED",
    )

    store.save(evidence)

    assert store.get("evidence-crud-1") == evidence
    assert store.get_by_execution("exec-evidence-crud") == evidence
    assert store.list_by_agent("agent-evidence-1") == [evidence]

    store.delete("evidence-crud-1")
    assert store.get("evidence-crud-1") is None


def test_in_memory_evidence_store_is_thread_safe() -> None:
    store = InMemoryEvidenceStore()
    collector = RuntimeEvidenceCollector(store)
    errors: list[Exception] = []

    def collect_many(prefix: str) -> None:
        try:
            for index in range(20):
                collector.collect_and_save(
                    execution_id=f"exec-{prefix}-{index}",
                    agent_id=f"agent-{prefix}",
                    correlation_id=f"corr-{prefix}-{index}",
                    status="COMPLETED",
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=collect_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(store.list_by_agent("agent-t0")) == 20


def test_collector_aggregates_runtime_inputs() -> None:
    store = InMemoryEvidenceStore()
    collector = RuntimeEvidenceCollector(store)
    permission_record = AuditRecord(
        audit_id="audit-perm-1",
        event_type="tool.permission.denied",
        execution_id="exec-evidence-1",
        agent_id="agent-evidence-1",
        correlation_id="corr-evidence-1",
        actor="agent-evidence-1",
        action="tool.permission.evaluate",
        resource="email.send",
        decision="DENY",
        severity="WARNING",
        metadata={"permission": "email.send", "reason": "blocked"},
    )
    runtime_event = RuntimeEventEnvelope(
        event_id="event-1",
        event_type=EXECUTION_START,
        correlation_id="corr-evidence-1",
        parent_event_id=None,
        execution_id="exec-evidence-1",
        payload={"task": "evidence task"},
    )
    execution_metric = ExecutionMetric(
        execution_id="exec-evidence-1",
        agent_id="agent-evidence-1",
        duration_ms=150,
        status="COMPLETED",
        step_count=2,
        tool_count=1,
        failure_count=0,
    )

    evidence = collector.collect(
        execution_id="exec-evidence-1",
        agent_id="agent-evidence-1",
        correlation_id="corr-evidence-1",
        status="COMPLETED",
        context_snapshot=_context_snapshot(),
        execution_state=_execution_state(),
        audit_records=[_audit_record(), permission_record],
        runtime_events=[runtime_event],
        execution_metric=execution_metric,
        permission_decisions=[
            PermissionDecision(
                execution_id="exec-evidence-1",
                decision="DENY",
                tool_name="email.send",
                permission="email.send",
            )
        ],
    )

    assert evidence.execution_id == "exec-evidence-1"
    assert evidence.state_snapshot is not None
    assert evidence.state_snapshot.plan_id == "plan-evidence-1"
    assert evidence.checkpoint_summary is not None
    assert evidence.checkpoint_summary.checkpoint_id == "checkpoint-evidence-1"
    assert evidence.memory_snapshot is not None
    assert evidence.memory_snapshot.namespace == "memory-ns-1"
    assert len(evidence.audit_records) == 2
    assert evidence.event_summary is not None
    assert evidence.event_summary.total_events == 1
    assert evidence.metrics_summary is not None
    assert evidence.metrics_summary.duration_ms == 150
    assert len(evidence.permission_decisions) == 1
    assert evidence.permission_decisions[0].decision == "DENY"


def test_collector_handles_empty_optional_components() -> None:
    store = InMemoryEvidenceStore()
    collector = RuntimeEvidenceCollector(store)

    evidence = collector.collect(
        execution_id="exec-evidence-empty",
        agent_id="agent-evidence-1",
        correlation_id=None,
        status="COMPLETED",
    )

    assert evidence.state_snapshot is None
    assert evidence.checkpoint_summary is None
    assert evidence.memory_snapshot is None
    assert evidence.audit_records == ()
    assert evidence.event_summary is None
    assert evidence.metrics_summary is None
    assert evidence.permission_decisions == ()


def test_pipeline_collects_completed_evidence() -> None:
    production_runtime = create_production_runtime()
    evidence_store = InMemoryEvidenceStore()
    evidence_collector = RuntimeEvidenceCollector(evidence_store)
    audit_store = InMemoryAuditStore()
    audit_recorder = RuntimeAuditRecorder(audit_store)
    analytics_store = InMemoryAnalyticsStore()
    analytics_collector = RuntimeAnalyticsCollector(analytics_store)
    event_publisher = InMemoryEventPublisher()
    state_store = InMemoryExecutionStateStore()
    checkpoint_store = InMemoryCheckpointStore()
    memory_manager = MemoryContextManager(InMemoryMemoryStore())
    context_manager = RuntimeContextManager()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        state_store=state_store,
        checkpoint_store=checkpoint_store,
        memory_manager=memory_manager,
        runtime_context_manager=context_manager,
        analytics_collector=analytics_collector,
        event_publisher=event_publisher,
        audit_recorder=audit_recorder,
        evidence_collector=evidence_collector,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-evidence-pipeline",
        agent_id="agent-evidence-1",
    )

    result = pipeline.run(_agent(), "evidence pipeline task", context)

    assert result.status == "COMPLETED"
    evidence = evidence_store.get_by_execution("exec-evidence-pipeline")
    assert evidence is not None
    assert evidence.status == "COMPLETED"
    assert evidence.state_snapshot is not None
    assert evidence.state_snapshot.status == "COMPLETED"
    assert evidence.checkpoint_summary is not None
    assert evidence.memory_snapshot is not None
    assert len(evidence.audit_records) >= 1
    assert evidence.event_summary is not None
    assert evidence.event_summary.total_events >= 2
    assert evidence.metrics_summary is not None
    assert evidence.metrics_summary.status == "COMPLETED"


def test_pipeline_collects_failed_evidence() -> None:
    production_runtime = create_production_runtime()
    evidence_store = InMemoryEvidenceStore()
    evidence_collector = RuntimeEvidenceCollector(evidence_store)
    audit_store = InMemoryAuditStore()
    audit_recorder = RuntimeAuditRecorder(audit_store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        audit_recorder=audit_recorder,
        evidence_collector=evidence_collector,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-evidence-fail",
        agent_id="agent-evidence-1",
    )

    with patch.object(
        pipeline._execution_pipeline,
        "run",
        side_effect=RuntimeError("evidence pipeline failure"),
    ):
        result = pipeline.run(_agent(), "failed evidence task", context)

    assert result.status == "FAILED"
    evidence = evidence_store.get_by_execution("exec-evidence-fail")
    assert evidence is not None
    assert evidence.status == "FAILED"
    assert len(evidence.audit_records) == 3
    assert any(record.event_type == "step.failed" for record in evidence.audit_records)


def test_pipeline_without_evidence_collector_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-evidence-legacy",
        agent_id="agent-evidence-1",
    )

    result = pipeline.run(_agent(), "legacy evidence task", context)

    assert result.status == "COMPLETED"
    assert pipeline._evidence_collector is None


def test_evidence_module_has_no_forbidden_dependencies() -> None:
    for path in _EVIDENCE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
