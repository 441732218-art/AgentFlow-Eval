# AgentFlow Intelligence v2.0 — Runtime observability tests (Phase 9.5)

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import attach_execution_context, attach_tool_request
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.observability.collector import InMemoryObservationCollector
from app.runtime.observability.events import RuntimeEvent, RuntimeEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.errors import RemoteProviderError
from app.runtime.tools.executor_registry import ToolExecutorRegistry
from app.runtime.tools.invocation_event import ToolInvocationEvent
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter
from app.runtime.tools.remote_client import InMemoryRemoteClient

_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_OBSERVABILITY_PATHS = (
    _RUNTIME_ROOT / "observability",
    _RUNTIME_ROOT / "executor",
    _RUNTIME_ROOT / "pipeline",
    _RUNTIME_ROOT / "tools",
)
_FORBIDDEN_RUNTIME_STRINGS = ("trade_provider", "trade.", "CRM", "Email")


def test_runtime_event_creation() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    event = RuntimeEvent(
        event_type=RuntimeEventType.EXECUTION_STARTED,
        timestamp=timestamp,
        execution_id="exec-1",
        agent_id="agent-1",
        tenant_id="tenant-1",
        metadata={"task": "run"},
    )

    assert event.execution_id == "exec-1"
    assert event.event_type == "execution.started"
    assert event.tool_name is None
    assert event.metadata == {"task": "run"}


def test_runtime_event_type_constants() -> None:
    assert RuntimeEventType.EXECUTION_STARTED == "execution.started"
    assert RuntimeEventType.EXECUTION_COMPLETED == "execution.completed"
    assert RuntimeEventType.TOOL_STARTED == "tool.started"
    assert RuntimeEventType.TOOL_COMPLETED == "tool.completed"
    assert RuntimeEventType.TOOL_FAILED == "tool.failed"


def test_collector_record_and_get_events() -> None:
    collector = InMemoryObservationCollector()
    event = RuntimeEvent(
        event_type=RuntimeEventType.TOOL_STARTED,
        timestamp=datetime.now(timezone.utc),
        execution_id="exec-2",
        agent_id="agent-2",
        tool_name="math.add",
    )

    collector.record(event)

    events = collector.get_events()
    assert len(events) == 1
    assert events[0].event_type == "tool.started"
    assert events[0].tool_name == "math.add"


def test_execution_context_carries_observation_collector() -> None:
    collector = InMemoryObservationCollector()
    execution_context = ExecutionContext(
        execution_id="exec-3",
        agent_id="agent-3",
        tenant_id="tenant-3",
        observation_collector=collector,
    )

    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            RuntimeEventType.EXECUTION_STARTED,
            metadata={"task": "observe"},
        ),
    )

    events = collector.get_events()
    assert len(events) == 1
    assert events[0].tenant_id == "tenant-3"
    assert events[0].metadata == {"task": "observe"}


class LocalProbeAdapter(ToolExecutorAdapter):
    executor_type = "local"

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = tool_definition, arguments, execution_context
        return {"ok": True}


def test_tool_success_produces_observation_events() -> None:
    collector = InMemoryObservationCollector()
    execution_context = ExecutionContext(
        execution_id="exec-4",
        agent_id="agent-4",
        observation_collector=collector,
    )
    registry = ToolExecutorRegistry()
    registry.register(LocalProbeAdapter())
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = ToolDefinition(
        name="probe.tool",
        description="Probe",
        executor_type="local",
        input_schema={"type": "object"},
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-4", agent_id="agent-4"),
        definition,
        {},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True}
    events = collector.get_events()
    event_types = [event.event_type for event in events]
    assert RuntimeEventType.TOOL_STARTED in event_types
    assert RuntimeEventType.TOOL_COMPLETED in event_types
    completed = next(
        event for event in events if event.event_type == RuntimeEventType.TOOL_COMPLETED
    )
    assert completed.tool_name == "probe.tool"
    assert completed.status == "success"
    assert completed.duration_ms is not None
    assert completed.duration_ms >= 0


class FailingLocalAdapter(ToolExecutorAdapter):
    executor_type = "local"

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = tool_definition, arguments, execution_context
        raise ValueError("tool failed")


def test_tool_failure_produces_failed_event() -> None:
    collector = InMemoryObservationCollector()
    execution_context = ExecutionContext(
        execution_id="exec-5",
        agent_id="agent-5",
        observation_collector=collector,
    )
    registry = ToolExecutorRegistry()
    registry.register(FailingLocalAdapter())
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = ToolDefinition(
        name="failing.tool",
        description="Fails",
        executor_type="local",
        input_schema={"type": "object"},
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-5", agent_id="agent-5"),
        definition,
        {},
    )
    attach_execution_context(runtime, execution_context)

    with pytest.raises(ValueError, match="tool failed"):
        execute_tool_via_engine(runtime, engine)

    failed = next(
        event
        for event in collector.get_events()
        if event.event_type == RuntimeEventType.TOOL_FAILED
    )
    assert failed.status == "failed"
    assert failed.metadata["error_type"] == "ValueError"


def test_remote_failure_produces_failed_event() -> None:
    collector = InMemoryObservationCollector()
    execution_context = ExecutionContext(
        execution_id="exec-6",
        agent_id="agent-6",
        observation_collector=collector,
    )

    def handler(_request: ToolProviderRequest) -> ToolProviderResponse:
        return ToolProviderResponse(success=False, error="provider failed")

    adapter = RemoteToolExecutorAdapter(
        InMemoryRemoteClient(handler=handler),
        policy=RemoteExecutionPolicy(max_retries=0),
    )
    definition = ToolDefinition(
        name="remote.fail",
        description="Remote failure",
        executor_type="remote",
        input_schema={"type": "object"},
        metadata={"endpoint": "http://mock.test/tools/invoke"},
    )

    with pytest.raises(RemoteProviderError):
        adapter.execute(definition, {"query": "x"}, execution_context=execution_context)

    events = collector.get_events()
    event_types = [event.event_type for event in events]
    assert RuntimeEventType.TOOL_STARTED in event_types
    assert RuntimeEventType.TOOL_FAILED in event_types
    failed = next(
        event for event in events if event.event_type == RuntimeEventType.TOOL_FAILED
    )
    assert failed.metadata["transport"] == "remote_client"
    assert failed.metadata["error_type"] == "RemoteProviderError"


def test_pipeline_without_collector_keeps_backward_compatible_behavior() -> None:
    registry = ToolExecutorRegistry()
    registry.register(LocalProbeAdapter())
    engine = ToolExecutionEngine(adapter_registry=registry)
    pipeline = ExecutionPipeline(tool_execution_engine=engine)
    definition = ToolDefinition(
        name="probe.optional",
        description="Optional collector",
        executor_type="local",
        input_schema={"type": "object"},
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-7", agent_id="agent-7"),
        definition,
        {},
    )

    output = pipeline.run(runtime, "task")

    assert output == {"ok": True}


class BrokenCollector:
    def record(self, _event: RuntimeEvent) -> None:
        raise RuntimeError("collector unavailable")

    def get_events(self) -> list[RuntimeEvent]:
        return []


def test_observation_failure_does_not_affect_execution() -> None:
    execution_context = ExecutionContext(
        execution_id="exec-8",
        agent_id="agent-8",
        observation_collector=BrokenCollector(),
    )
    registry = ToolExecutorRegistry()
    registry.register(LocalProbeAdapter())
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = ToolDefinition(
        name="probe.safe",
        description="Safe probe",
        executor_type="local",
        input_schema={"type": "object"},
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-8", agent_id="agent-8"),
        definition,
        {},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True}


def test_tool_invocation_event_extended_fields() -> None:
    event = ToolInvocationEvent(
        execution_id="exec-9",
        tool_name="example.tool",
        started_at=1.0,
        finished_at=2.5,
        status="success",
    )

    assert event.start_time == 1.0
    assert event.end_time == 2.5
    assert event.duration_ms == 1500.0


def test_tool_invocation_event_normalizes_legacy_error_status() -> None:
    event = ToolInvocationEvent(
        execution_id="exec-10",
        tool_name="example.tool",
        started_at=0.0,
        finished_at=1.0,
        status="error",
        error_type="RemoteProviderError",
    )

    assert event.status == "failed"
    assert event.duration_ms == 1000.0


def test_execution_context_to_remote_payload_unchanged_with_collector() -> None:
    collector = InMemoryObservationCollector()
    execution_context = ExecutionContext(
        execution_id="exec-11",
        agent_id="agent-11",
        tenant_id="tenant-11",
        observation_collector=collector,
    )

    assert execution_context.to_remote_payload() == {
        "execution_id": "exec-11",
        "agent_id": "agent-11",
        "tenant_id": "tenant-11",
    }


def test_runtime_observability_has_no_business_leakage() -> None:
    for root in _OBSERVABILITY_PATHS:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for forbidden in _FORBIDDEN_RUNTIME_STRINGS:
                assert forbidden not in source, f"{forbidden!r} found in {path}"
