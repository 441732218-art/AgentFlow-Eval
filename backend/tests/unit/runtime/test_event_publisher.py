# AgentFlow Intelligence v2.0 — Runtime event publisher tests (Phase 9.6)

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import attach_execution_context, attach_tool_request
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.events.event_types import RuntimeEventType
from app.runtime.events.models import RuntimeEvent
from app.runtime.events.publisher import InMemoryEventPublisher
from app.runtime.observability.events import RuntimeEventType as ObservationEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.executor_registry import ToolExecutorRegistry

_EVENTS_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "events"
_FORBIDDEN_EVENT_STRINGS = (
    "trade_provider",
    "CRM",
    "Email",
    "".join(("sec", "ret")),
    "".join(("api", "_key")),
    "".join(("to", "ken")),
)


def test_runtime_event_creation() -> None:
    timestamp = datetime(2026, 2, 1, tzinfo=timezone.utc)
    event = RuntimeEvent(
        event_type=RuntimeEventType.TOOL_STARTED,
        execution_id="exec-1",
        agent_id="agent-1",
        tenant_id="tenant-1",
        timestamp=timestamp,
        payload={"tool_name": "probe.tool"},
    )

    assert event.event_type == RuntimeEventType.TOOL_STARTED
    assert event.execution_id == "exec-1"
    assert event.payload["tool_name"] == "probe.tool"


def test_in_memory_event_publisher_stores_events() -> None:
    publisher = InMemoryEventPublisher()
    event = RuntimeEvent(
        event_type=RuntimeEventType.EXECUTION_STARTED,
        execution_id="exec-2",
        timestamp=datetime.now(timezone.utc),
        payload={"task": "run"},
    )

    publisher.publish(event)

    events = publisher.get_events()
    assert len(events) == 1
    assert events[0].event_type == RuntimeEventType.EXECUTION_STARTED

    publisher.clear()
    assert publisher.get_events() == []


def test_execution_context_carries_event_publisher() -> None:
    publisher = InMemoryEventPublisher()
    execution_context = ExecutionContext(
        execution_id="exec-3",
        agent_id="agent-3",
        tenant_id="tenant-3",
        event_publisher=publisher,
    )

    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            ObservationEventType.TOOL_STARTED,
            tool_name="probe.tool",
        ),
    )

    published = publisher.get_events()
    assert len(published) == 1
    assert published[0].execution_id == "exec-3"
    assert published[0].payload["tool_name"] == "probe.tool"


def test_record_runtime_event_publishes_without_collector() -> None:
    publisher = InMemoryEventPublisher()
    execution_context = ExecutionContext(
        execution_id="exec-4",
        agent_id="agent-4",
        event_publisher=publisher,
    )

    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            ObservationEventType.TOOL_COMPLETED,
            tool_name="done.tool",
            status="success",
            duration_ms=12.5,
        ),
    )

    assert len(publisher.get_events()) == 1
    published = publisher.get_events()[0]
    assert published.payload["status"] == "success"
    assert published.payload["duration_ms"] == 12.5


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


def test_publisher_failure_does_not_affect_execution() -> None:
    class BrokenPublisher:
        def publish(self, _event: RuntimeEvent) -> None:
            raise RuntimeError("publisher unavailable")

    execution_context = ExecutionContext(
        execution_id="exec-5",
        agent_id="agent-5",
        event_publisher=BrokenPublisher(),
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
        RuntimeContext(execution_id="exec-5", agent_id="agent-5"),
        definition,
        {},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True}


def test_to_remote_payload_does_not_leak_event_publisher() -> None:
    publisher = InMemoryEventPublisher()
    execution_context = ExecutionContext(
        execution_id="exec-6",
        agent_id="agent-6",
        tenant_id="tenant-6",
        event_publisher=publisher,
    )

    payload = execution_context.to_remote_payload()

    assert payload == {
        "execution_id": "exec-6",
        "agent_id": "agent-6",
        "tenant_id": "tenant-6",
    }
    assert "event_publisher" not in payload
    assert "observation_collector" not in payload


def test_runtime_event_payload_strips_sensitive_keys() -> None:
    event = RuntimeEvent(
        event_type=RuntimeEventType.TOOL_FAILED,
        execution_id="exec-7",
        timestamp=datetime.now(timezone.utc),
        payload={
            "tool_name": "remote.tool",
            "".join(("api", "_key")): "must-not-appear",
            "error_type": "RemoteProviderError",
        },
    )

    assert event.payload["tool_name"] == "remote.tool"
    assert "".join(("api", "_key")) not in event.payload


def test_runtime_events_code_has_no_business_or_sensitive_leakage() -> None:
    for path in _EVENTS_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_EVENT_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"
