# AgentFlow Intelligence v2.0 — Agent planning tests (Phase 10.4)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.planning import DefaultPlanner, ExecutionPlan
from app.runtime.planning.planner import Planner

_PLANNING_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "planning"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email", "openai", "langgraph")


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-plan-1",
        name="planning-agent",
        tool_names=["probe.echo"],
    )


def _context(production_runtime) -> ExecutionContext:
    return create_execution_context(
        production_runtime,
        execution_id="exec-plan-1",
        agent_id="agent-plan-1",
    )


def test_execution_plan_creation() -> None:
    plan = ExecutionPlan(
        plan_id="plan-1",
        agent_id="agent-plan-1",
        steps=(
            ExecutionStep(name="execute", step_type="execute", status="PENDING"),
        ),
        metadata={"source": "test"},
    )

    assert plan.plan_id == "plan-1"
    assert plan.agent_id == "agent-plan-1"
    assert len(plan.steps) == 1
    assert plan.metadata["source"] == "test"


def test_planner_interface_is_structural() -> None:
    planner = DefaultPlanner()
    assert isinstance(planner, Planner)


def test_default_planner_generates_plan() -> None:
    production_runtime = create_production_runtime()
    planner = DefaultPlanner()
    context = _context(production_runtime)

    plan = planner.create_plan(_agent(), "plan task", context)

    assert plan.agent_id == "agent-plan-1"
    assert len(plan.steps) == 1
    assert plan.steps[0].step_type == "execute"
    assert plan.steps[0].metadata["task"] == "plan task"


def test_pipeline_executes_planner_output() -> None:
    production_runtime = create_production_runtime()

    class StubPlanner:
        def create_plan(self, agent_definition, task, context):
            _ = agent_definition, context
            return ExecutionPlan(
                plan_id="plan-stub",
                agent_id="agent-plan-1",
                steps=(
                    ExecutionStep(
                        name="execute",
                        step_type="execute",
                        status="PENDING",
                        metadata={"task": task},
                    ),
                ),
            )

    pipeline = AgentExecutionPipeline(production_runtime, planner=StubPlanner())
    result = pipeline.run(_agent(), "stub task", _context(production_runtime))

    assert result.status == "COMPLETED"
    assert result.metadata["plan_id"] == "plan-stub"
    assert len(result.steps) == 2
    assert result.steps[-1].step_type == "execute"
    assert result.steps[-1].status == "COMPLETED"


def test_pipeline_without_planner_uses_default_planner() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    result = pipeline.run(_agent(), "default task", _context(production_runtime))

    assert result.status == "COMPLETED"
    assert result.metadata["plan_id"]
    assert len(result.steps) == 2
    assert result.output == "pipeline execution completed"


def test_planning_has_no_applications_dependency() -> None:
    for path in _PLANNING_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source.lower(), f"{forbidden!r} found in {path}"
