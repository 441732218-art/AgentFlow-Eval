# AgentFlow Intelligence v2.0 — Agent execution pipeline tests (Phase 10.3)

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.observability.events import RuntimeEventType as ObservationEventType
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.pipeline.steps import complete_step, create_step, fail_step

_PIPELINE_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "pipeline"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email")


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-pipeline-1",
        name="pipeline-agent",
        tool_names=["probe.echo"],
    )


def _context(production_runtime) -> ExecutionContext:
    return create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-1",
        agent_id="agent-pipeline-1",
        tenant_id="tenant-1",
    )


def test_execution_step_creation_and_helpers() -> None:
    step = create_step("prepare", "agent.prepare", metadata={"phase": "init"})
    assert isinstance(step, ExecutionStep)
    assert step.name == "prepare"
    assert step.status == "RUNNING"

    complete_step(step)
    assert step.status == "COMPLETED"

    failed = create_step("execute", "agent.execute")
    fail_step(failed, RuntimeError("step failed"))
    assert failed.status == "FAILED"
    assert failed.metadata["error_type"] == "RuntimeError"


def test_pipeline_successful_execution() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = _context(production_runtime)

    result = pipeline.run(_agent(), "pipeline task", context)

    assert result.status == "COMPLETED"
    assert result.execution_id == "exec-pipeline-1"
    assert result.agent_id == "agent-pipeline-1"
    assert len(result.steps) == 2
    assert all(step.status == "COMPLETED" for step in result.steps)
    assert result.output == "pipeline execution completed"


def test_pipeline_failure_handling() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = _context(production_runtime)

    with patch.object(
        pipeline._execution_pipeline,
        "run",
        side_effect=RuntimeError("pipeline failed"),
    ):
        result = pipeline.run(_agent(), "failing task", context)

    assert result.status == "FAILED"
    assert result.output is None
    assert result.metadata["error_message"] == "pipeline failed"
    assert result.steps[-1].status == "FAILED"


def test_agent_runtime_uses_pipeline() -> None:
    production_runtime = create_production_runtime()
    agent_runtime = AgentRuntime(production_runtime)
    context = _context(production_runtime)

    result = agent_runtime.execute(_agent(), "runtime task", context=context)

    assert result.session.status == "COMPLETED"
    assert result.pipeline_result is not None
    assert result.pipeline_result.status == "COMPLETED"
    assert len(result.pipeline_result.steps) == 2


def test_governance_context_preserved_through_pipeline() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = _context(production_runtime)

    pipeline.run(_agent(), "governance task", context)

    assert context.observation_collector is production_runtime.observation_collector
    assert context.event_publisher is production_runtime.event_publisher
    assert context.governance_lifecycle is production_runtime.governance_lifecycle

    observations = production_runtime.observation_collector.get_events()
    assert any(event.event_type == ObservationEventType.AGENT_STARTED for event in observations)
    assert any(event.event_type == ObservationEventType.AGENT_COMPLETED for event in observations)


def test_agent_pipeline_has_no_applications_dependency() -> None:
    for path in _PIPELINE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"
