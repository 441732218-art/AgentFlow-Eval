# AgentFlow Intelligence v2.0 — Runtime audit tests (Phase 11.3)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.audit.memory_store import InMemoryAuditStore
from app.runtime.audit.models import AuditRecord
from app.runtime.audit.recorder import RuntimeAuditRecorder
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.event_stream.models import EXECUTION_FAILED, EXECUTION_START
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.policy.models import PolicyDeniedError
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability

_AUDIT_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "audit"
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
)


def _record() -> AuditRecord:
    return AuditRecord(
        audit_id="audit-11-1",
        event_type="execution.start",
        execution_id="exec-audit-1",
        agent_id="agent-audit-1",
        correlation_id="corr-audit-1",
        actor="agent-audit-1",
        action="execution.start",
        resource="execution",
        decision="ALLOW",
        severity="INFO",
        metadata={"task": "audit task"},
    )


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-audit-1",
        name="audit-agent",
        tool_names=["email.send"],
    )


def _capability() -> ToolCapability:
    return ToolCapability(
        tool_name="email.send",
        version="1.0",
        description="Send email",
        permission_scope=("email.send",),
    )


def test_audit_record_creation() -> None:
    record = _record()

    assert record.audit_id == "audit-11-1"
    assert record.event_type == "execution.start"
    assert record.execution_id == "exec-audit-1"
    assert record.agent_id == "agent-audit-1"
    assert record.correlation_id == "corr-audit-1"
    assert record.decision == "ALLOW"
    assert record.severity == "INFO"
    assert record.metadata["task"] == "audit task"


def test_audit_record_is_immutable() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        record.decision = "DENY"  # type: ignore[misc]

    updated = record.with_updates(decision="DENY", severity="WARNING")
    assert updated.decision == "DENY"
    assert record.decision == "ALLOW"


def test_audit_store_crud() -> None:
    store = InMemoryAuditStore()
    record = _record()

    store.record(record)

    assert store.get("audit-11-1") == record
    assert store.list_by_execution("exec-audit-1") == [record]
    assert store.list_by_agent("agent-audit-1") == [record]

    store.delete("audit-11-1")
    assert store.get("audit-11-1") is None


def test_in_memory_audit_store_is_thread_safe() -> None:
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)
    errors: list[Exception] = []

    def record_many(prefix: str) -> None:
        try:
            for index in range(20):
                recorder.record_execution_event(
                    event_type="execution.start",
                    execution_id=f"exec-{prefix}",
                    agent_id=f"agent-{prefix}",
                    metadata={"index": index},
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=record_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(store.list_by_execution("exec-t0")) == 20


def test_runtime_audit_recorder_records_execution_event() -> None:
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)

    record = recorder.record_execution_event(
        event_type=EXECUTION_START,
        execution_id="exec-recorder-1",
        agent_id="agent-recorder-1",
        correlation_id="corr-recorder-1",
        metadata={"task": "recorder task"},
    )

    assert store.get(record.audit_id) == record
    assert record.decision == "ALLOW"
    assert record.severity == "INFO"


def test_runtime_audit_recorder_records_permission_deny() -> None:
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)

    record = recorder.record_permission_event(
        event_type="tool.permission.denied",
        execution_id="exec-perm-1",
        agent_id="agent-perm-1",
        resource="email.send",
        metadata={"reason": "blocked"},
    )

    assert record.decision == "DENY"
    assert record.event_type == "tool.permission.denied"
    assert record.resource == "email.send"
    assert record.severity == "WARNING"


def test_runtime_audit_recorder_records_failure_event() -> None:
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)

    record = recorder.record_failure_event(
        event_type="step.failed",
        execution_id="exec-fail-1",
        agent_id="agent-fail-1",
        resource="execute",
        error="boom",
    )

    assert record.decision == "FAILED"
    assert record.severity == "ERROR"
    assert record.metadata["error"] == "boom"


def test_pipeline_audit_integration() -> None:
    production_runtime = create_production_runtime()
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        audit_recorder=recorder,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-audit-pipeline",
        agent_id="agent-audit-1",
    )

    result = pipeline.run(_agent(), "audit pipeline task", context)

    assert result.status == "COMPLETED"
    records = store.list_by_execution("exec-audit-pipeline")
    assert len(records) == 1
    assert records[0].event_type == EXECUTION_START
    assert records[0].decision == "ALLOW"


def test_agent_runtime_records_permission_deny_audit() -> None:
    production_runtime = create_production_runtime()
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)
    tool_registry = InMemoryToolRegistry()
    tool_registry.register(_capability())
    runtime = AgentRuntime(
        production_runtime,
        tool_registry=tool_registry,
        permission_evaluator=PermissionEvaluator(
            InMemoryPolicyEngine(blocked_tools=["email.send"]),
        ),
        audit_recorder=recorder,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-audit-perm",
        agent_id="agent-audit-1",
    )

    with pytest.raises(PolicyDeniedError, match="email.send"):
        runtime.execute(_agent(), "permission audit task", context)

    records = store.list_by_execution("exec-audit-perm")
    assert len(records) == 1
    assert records[0].event_type == "tool.permission.denied"
    assert records[0].decision == "DENY"


def test_pipeline_records_failure_audit_events() -> None:
    production_runtime = create_production_runtime()
    store = InMemoryAuditStore()
    recorder = RuntimeAuditRecorder(store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        audit_recorder=recorder,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-audit-fail",
        agent_id="agent-audit-1",
    )

    with patch.object(
        pipeline._execution_pipeline,
        "run",
        side_effect=RuntimeError("audit pipeline failure"),
    ):
        result = pipeline.run(_agent(), "failed audit task", context)

    assert result.status == "FAILED"
    records = store.list_by_execution("exec-audit-fail")
    event_types = [record.event_type for record in records]
    assert event_types == [EXECUTION_START, "step.failed", EXECUTION_FAILED]
    assert records[1].decision == "FAILED"
    assert records[2].decision == "FAILED"


def test_pipeline_without_audit_recorder_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-audit-legacy",
        agent_id="agent-audit-1",
    )

    result = pipeline.run(_agent(), "legacy audit task", context)

    assert result.status == "COMPLETED"
    assert pipeline._audit_recorder is None


def test_audit_module_has_no_forbidden_dependencies() -> None:
    for path in _AUDIT_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
