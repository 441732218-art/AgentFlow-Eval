# AgentFlow Intelligence v2.0 — Runtime correlation tests (Phase 10.11)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.correlation.context import get_correlation_context
from app.runtime.correlation.manager import RuntimeCorrelationManager
from app.runtime.correlation.models import CorrelationContext
from app.runtime.observability.events import RuntimeEventType

from app.runtime.observability.recording import build_runtime_event
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

_CORRELATION_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "correlation"
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "opentelemetry",
    "openai",
    "langgraph",
)


def _correlation(
    *,
    correlation_id: str = "corr-root",
    execution_id: str = "exec-corr-1",
    span_id: str = "span-root",
    parent_id: str | None = None,
) -> CorrelationContext:
    return CorrelationContext(
        correlation_id=correlation_id,
        execution_id=execution_id,
        parent_id=parent_id,
        span_id=span_id,
    )


def test_correlation_context_creation() -> None:
    context = _correlation()

    assert context.correlation_id == "corr-root"
    assert context.execution_id == "exec-corr-1"
    assert context.parent_id is None
    assert context.span_id == "span-root"


def test_correlation_context_update_returns_new_immutable_instance() -> None:
    context = _correlation()
    updated = context.with_updates(parent_id="span-parent")

    assert updated is not context
    assert updated.parent_id == "span-parent"
    assert context.parent_id is None


def test_runtime_correlation_manager_child_relationship() -> None:
    manager = RuntimeCorrelationManager()
    execution = manager.create_execution_context("exec-child-1")
    step = manager.create_child_context(execution)
    tool = manager.create_child_context(step)

    assert step.parent_id == execution.span_id
    assert step.correlation_id == execution.correlation_id
    assert tool.parent_id == step.span_id
    assert tool.correlation_id == execution.correlation_id


def test_runtime_correlation_manager_lifecycle() -> None:
    manager = RuntimeCorrelationManager()
    execution = manager.create_execution_context("exec-life-1")
    step = manager.create_child_context(execution)

    assert manager.get_context(execution.span_id) == execution
    assert manager.get_context(step.span_id) == step

    manager.close_context(step.span_id)
    assert manager.get_context(step.span_id) is None
    assert manager.get_context(execution.span_id) == execution

    manager.close_context(execution.span_id)
    assert manager.get_context(execution.span_id) is None


def test_runtime_correlation_manager_execution_context() -> None:
    manager = RuntimeCorrelationManager()

    execution = manager.create_execution_context("exec-root-1")

    assert execution.correlation_id == execution.span_id
    assert execution.parent_id is None
    assert execution.execution_id == "exec-root-1"


def test_runtime_event_includes_correlation_fields() -> None:
    correlation = _correlation(
        correlation_id="corr-event",
        span_id="span-event",
        parent_id="span-parent",
    )

    event = build_runtime_event(
        None,
        RuntimeEventType.TOOL_STARTED,
        correlation=correlation,
    )

    assert event.correlation_id == "corr-event"
    assert event.parent_event_id == "span-parent"
    assert event.span_id == "span-event"


def test_pipeline_integrates_runtime_correlation_manager() -> None:
    production_runtime = create_production_runtime()
    correlation_manager = RuntimeCorrelationManager()
    recorded_correlations: list[CorrelationContext | None] = []
    pipeline = AgentExecutionPipeline(
        production_runtime,
        correlation_manager=correlation_manager,
    )

    def _record_tool_correlation(runtime_context: RuntimeContext, task: str) -> str:
        _ = task
        recorded_correlations.append(get_correlation_context(runtime_context))
        return "ok"

    pipeline._execution_pipeline = type(
        "StubPipeline",
        (),
        {"run": staticmethod(_record_tool_correlation)},
    )()
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-correlation",
        agent_id="agent-correlation",
    )
    agent = AgentDefinition(
        id="agent-correlation",
        name="correlation-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "correlation task", context)

    assert result.status == "COMPLETED"
    assert len(recorded_correlations) == 1
    tool_correlation = recorded_correlations[0]
    assert tool_correlation is not None
    assert tool_correlation.parent_id is not None
    assert correlation_manager.get_context(tool_correlation.span_id) is None


def test_pipeline_without_correlation_manager_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-no-correlation-manager",
        agent_id="agent-no-correlation-manager",
    )
    agent = AgentDefinition(
        id="agent-no-correlation-manager",
        name="no-correlation-manager-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "no correlation manager task", context)

    assert result.status == "COMPLETED"
    assert len(result.steps) == 2


def test_runtime_correlation_manager_isolates_executions() -> None:
    manager = RuntimeCorrelationManager()
    first = manager.create_execution_context("exec-isolation-1")
    second = manager.create_execution_context("exec-isolation-2")

    assert first.correlation_id != second.correlation_id
    assert manager.get_context(first.span_id) == first
    assert manager.get_context(second.span_id) == second


def test_runtime_correlation_has_no_forbidden_dependencies() -> None:
    for path in _CORRELATION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
