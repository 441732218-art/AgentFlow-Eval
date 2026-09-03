# AgentFlow Intelligence v2.0 — Runtime analytics tests (Phase 11.1)

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.analytics.collector import RuntimeAnalyticsCollector
from app.runtime.analytics.memory_store import InMemoryAnalyticsStore
from app.runtime.analytics.models import ExecutionMetric, StepMetric, ToolMetric
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import attach_execution_context, attach_tool_request
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.tools.definition import ToolDefinition

_ANALYTICS_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "analytics"
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
)


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-analytics-1",
        name="analytics-agent",
        tool_names=["probe.echo"],
    )


def _execution_metric() -> ExecutionMetric:
    return ExecutionMetric(
        execution_id="exec-analytics-1",
        agent_id="agent-analytics-1",
        duration_ms=120,
        status="COMPLETED",
        step_count=2,
        tool_count=1,
        failure_count=0,
        metadata={"task": "analytics task"},
    )


def test_execution_metric_creation() -> None:
    metric = _execution_metric()

    assert metric.execution_id == "exec-analytics-1"
    assert metric.agent_id == "agent-analytics-1"
    assert metric.duration_ms == 120
    assert metric.status == "COMPLETED"
    assert metric.step_count == 2
    assert metric.tool_count == 1
    assert metric.failure_count == 0
    assert metric.metadata["task"] == "analytics task"
    assert metric.created_at is not None


def test_metric_models_are_immutable() -> None:
    metric = _execution_metric()

    with pytest.raises(FrozenInstanceError):
        metric.duration_ms = 999  # type: ignore[misc]

    updated = metric.with_updates(duration_ms=999)
    assert updated.duration_ms == 999
    assert metric.duration_ms == 120


def test_runtime_analytics_collector_persists_metrics() -> None:
    store = InMemoryAnalyticsStore()
    collector = RuntimeAnalyticsCollector(store)
    execution_metric = _execution_metric()
    step_metric = StepMetric(
        execution_id="exec-analytics-1",
        step_id="execute",
        duration_ms=45,
        status="COMPLETED",
    )
    tool_metric = ToolMetric(
        execution_id="exec-analytics-1",
        tool_name="probe.echo",
        duration_ms=30,
        status="COMPLETED",
    )

    collector.collect_execution_metric(execution_metric)
    collector.collect_step_metric(step_metric)
    collector.collect_tool_metric(tool_metric)

    assert collector.store.get_execution_metrics() == [execution_metric]
    assert collector.store.get_step_metrics() == [step_metric]
    assert collector.store.get_tool_metrics() == [tool_metric]


def test_in_memory_analytics_store_is_thread_safe_and_filterable() -> None:
    store = InMemoryAnalyticsStore()
    first = _execution_metric()
    second = ExecutionMetric(
        execution_id="exec-analytics-2",
        agent_id="agent-analytics-2",
        duration_ms=80,
        status="FAILED",
        step_count=1,
        tool_count=0,
        failure_count=1,
    )

    store.save_execution_metric(first)
    store.save_execution_metric(second)

    assert store.get_execution_metrics("exec-analytics-1") == [first]
    assert len(store.get_execution_metrics()) == 2

    store.clear()
    assert store.get_execution_metrics() == []


def test_pipeline_integration_collects_execution_and_step_metrics() -> None:
    production_runtime = create_production_runtime()
    store = InMemoryAnalyticsStore()
    collector = RuntimeAnalyticsCollector(store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        analytics_collector=collector,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-analytics-pipeline",
        agent_id="agent-analytics-1",
    )

    result = pipeline.run(_agent(), "analytics pipeline task", context)

    assert result.status == "COMPLETED"
    execution_metrics = store.get_execution_metrics("exec-analytics-pipeline")
    step_metrics = store.get_step_metrics("exec-analytics-pipeline")

    assert len(execution_metrics) == 1
    assert execution_metrics[0].agent_id == "agent-analytics-1"
    assert execution_metrics[0].status == "COMPLETED"
    assert execution_metrics[0].step_count == 1
    assert execution_metrics[0].duration_ms >= 0
    assert len(step_metrics) == 1
    assert step_metrics[0].step_id == "execute"
    assert step_metrics[0].status == "COMPLETED"


def test_pipeline_collects_tool_metric_when_tool_executed() -> None:
    production_runtime = create_production_runtime()
    adapter = production_runtime.tool_execution_engine.adapter_registry.get("local")
    assert adapter is not None
    adapter.handler_registry.register("probe.echo", lambda message: {"echo": message})

    store = InMemoryAnalyticsStore()
    collector = RuntimeAnalyticsCollector(store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        analytics_collector=collector,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-analytics-tool",
        agent_id="agent-analytics-1",
    )
    tool_definition = ToolDefinition(
        name="probe.echo",
        description="Analytics probe",
        executor_type="local",
        input_schema={"type": "object"},
    )

    original_run = pipeline._execution_pipeline.run

    def run_with_tool(runtime_context: RuntimeContext, task: str) -> object:
        attach_tool_request(runtime_context, tool_definition, {"message": "hello"})
        attach_execution_context(runtime_context, context)
        return original_run(runtime_context, task)

    with patch.object(pipeline._execution_pipeline, "run", side_effect=run_with_tool):
        result = pipeline.run(_agent(), "tool analytics task", context)

    assert result.status == "COMPLETED"
    tool_metrics = store.get_tool_metrics("exec-analytics-tool")
    execution_metrics = store.get_execution_metrics("exec-analytics-tool")

    assert len(tool_metrics) == 1
    assert tool_metrics[0].tool_name == "probe.echo"
    assert tool_metrics[0].status == "COMPLETED"
    assert execution_metrics[0].tool_count == 1


def test_pipeline_without_analytics_collector_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-analytics-legacy",
        agent_id="agent-analytics-1",
    )

    result = pipeline.run(_agent(), "legacy analytics task", context)

    assert result.status == "COMPLETED"
    assert pipeline._analytics_collector is None


def test_pipeline_records_failed_execution_analytics() -> None:
    production_runtime = create_production_runtime()
    store = InMemoryAnalyticsStore()
    collector = RuntimeAnalyticsCollector(store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        analytics_collector=collector,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-analytics-fail",
        agent_id="agent-analytics-1",
    )

    with patch.object(
        pipeline._execution_pipeline,
        "run",
        side_effect=RuntimeError("analytics failure"),
    ):
        result = pipeline.run(_agent(), "failed analytics task", context)

    assert result.status == "FAILED"
    execution_metrics = store.get_execution_metrics("exec-analytics-fail")
    step_metrics = store.get_step_metrics("exec-analytics-fail")

    assert len(execution_metrics) == 1
    assert execution_metrics[0].status == "FAILED"
    assert execution_metrics[0].failure_count == 1
    assert len(step_metrics) == 1
    assert step_metrics[0].status == "FAILED"
    assert step_metrics[0].error == "analytics failure"


def test_analytics_module_has_no_forbidden_dependencies() -> None:
    for path in _ANALYTICS_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
