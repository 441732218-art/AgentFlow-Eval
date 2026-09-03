# AgentFlow Intelligence v2.0 — Runtime event stream tests (Phase 11.2)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.correlation.manager import RuntimeCorrelationManager
from app.runtime.event_stream import (
    EXECUTION_COMPLETE,
    EXECUTION_FAILED,
    EXECUTION_START,
    STEP_COMPLETE,
    STEP_FAILED,
    STEP_START,
    InMemoryEventPublisher,
    RuntimeEventEnvelope,
)
from app.runtime.event_stream.consumer import EventConsumer
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

_EVENT_STREAM_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "event_stream"
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


def _envelope() -> RuntimeEventEnvelope:
    return RuntimeEventEnvelope(
        event_id="evt-1",
        event_type=EXECUTION_START,
        correlation_id="corr-1",
        parent_event_id=None,
        execution_id="exec-stream-1",
        payload={"task": "stream task"},
    )


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-stream-1",
        name="stream-agent",
        tool_names=["probe.echo"],
    )


def test_runtime_event_envelope_is_immutable() -> None:
    envelope = _envelope()

    with pytest.raises(FrozenInstanceError):
        envelope.event_type = STEP_START  # type: ignore[misc]

    updated = envelope.with_updates(event_type=STEP_START)
    assert updated.event_type == STEP_START
    assert envelope.event_type == EXECUTION_START


def test_in_memory_event_publisher_publish_and_get() -> None:
    publisher = InMemoryEventPublisher()
    envelope = _envelope()

    publisher.publish(envelope)

    assert publisher.get("evt-1") == envelope
    assert publisher.get("missing") is None


def test_in_memory_event_publisher_list_filters() -> None:
    publisher = InMemoryEventPublisher()
    first = _envelope()
    second = RuntimeEventEnvelope(
        event_id="evt-2",
        event_type=STEP_START,
        correlation_id="corr-1",
        parent_event_id="evt-1",
        execution_id="exec-stream-1",
        payload={"step_id": "execute"},
    )
    third = RuntimeEventEnvelope(
        event_id="evt-3",
        event_type=EXECUTION_START,
        correlation_id="corr-2",
        parent_event_id=None,
        execution_id="exec-stream-2",
        payload={},
    )

    publisher.publish(first)
    publisher.publish(second)
    publisher.publish(third)

    assert len(publisher.list()) == 3
    assert len(publisher.list(execution_id="exec-stream-1")) == 2
    assert len(publisher.list(event_type=EXECUTION_START)) == 2
    assert publisher.list(execution_id="exec-stream-1", event_type=STEP_START) == [second]

    publisher.clear()
    assert publisher.list() == []


def test_in_memory_event_publisher_is_thread_safe() -> None:
    publisher = InMemoryEventPublisher()
    errors: list[Exception] = []

    def publish_many(prefix: str) -> None:
        try:
            for index in range(20):
                publisher.publish(
                    RuntimeEventEnvelope(
                        event_id=f"{prefix}-{index}",
                        event_type=STEP_START,
                        correlation_id=prefix,
                        parent_event_id=None,
                        execution_id=f"exec-{prefix}",
                        payload={"index": index},
                    )
                )
        except Exception as exc:  # pragma: no cover - surfaced via errors
            errors.append(exc)

    threads = [threading.Thread(target=publish_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(publisher.list()) == 80


class RecordingConsumer:
    def __init__(self) -> None:
        self.events: list[RuntimeEventEnvelope] = []

    def consume(self, event: RuntimeEventEnvelope) -> None:
        self.events.append(event)


def test_event_consumer_protocol_is_usable() -> None:
    consumer: EventConsumer = RecordingConsumer()
    envelope = _envelope()

    consumer.consume(envelope)

    assert isinstance(consumer, RecordingConsumer)
    assert consumer.events == [envelope]


def test_pipeline_publishes_execution_lifecycle_events() -> None:
    production_runtime = create_production_runtime()
    publisher = InMemoryEventPublisher()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        event_publisher=publisher,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-stream-pipeline",
        agent_id="agent-stream-1",
    )

    result = pipeline.run(_agent(), "stream pipeline task", context)

    assert result.status == "COMPLETED"
    events = publisher.list(execution_id="exec-stream-pipeline")
    event_types = [event.event_type for event in events]

    assert event_types == [
        EXECUTION_START,
        STEP_START,
        STEP_COMPLETE,
        EXECUTION_COMPLETE,
    ]
    assert events[0].parent_event_id is None
    assert events[1].parent_event_id == events[0].event_id
    assert events[2].parent_event_id == events[1].event_id
    assert events[3].parent_event_id == events[2].event_id


def test_pipeline_publishes_failed_execution_events() -> None:
    production_runtime = create_production_runtime()
    publisher = InMemoryEventPublisher()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        event_publisher=publisher,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-stream-fail",
        agent_id="agent-stream-1",
    )

    with patch.object(
        pipeline._execution_pipeline,
        "run",
        side_effect=RuntimeError("stream failure"),
    ):
        result = pipeline.run(_agent(), "failed stream task", context)

    assert result.status == "FAILED"
    events = publisher.list(execution_id="exec-stream-fail")
    event_types = [event.event_type for event in events]

    assert event_types == [
        EXECUTION_START,
        STEP_START,
        STEP_FAILED,
        EXECUTION_FAILED,
    ]
    assert events[2].payload["error"] == "stream failure"


def test_pipeline_propagates_correlation_id_to_stream_events() -> None:
    production_runtime = create_production_runtime()
    publisher = InMemoryEventPublisher()
    correlation_manager = RuntimeCorrelationManager()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        correlation_manager=correlation_manager,
        event_publisher=publisher,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-stream-corr",
        agent_id="agent-stream-1",
    )

    pipeline.run(_agent(), "correlation stream task", context)

    events = publisher.list(execution_id="exec-stream-corr")
    execution_start = events[0]
    step_start = events[1]

    assert execution_start.event_type == EXECUTION_START
    assert step_start.event_type == STEP_START
    assert execution_start.correlation_id == step_start.correlation_id
    assert execution_start.correlation_id != "exec-stream-corr"


def test_pipeline_without_event_publisher_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-stream-legacy",
        agent_id="agent-stream-1",
    )

    result = pipeline.run(_agent(), "legacy stream task", context)

    assert result.status == "COMPLETED"
    assert pipeline._event_publisher is None


def test_event_stream_module_has_no_forbidden_dependencies() -> None:
    for path in _EVENT_STREAM_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
