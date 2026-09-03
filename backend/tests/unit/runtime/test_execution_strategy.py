# AgentFlow Intelligence v2.0 — Execution strategy tests (Phase 10.5)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.execution.executor import StepExecutionContext, StepExecutor
from app.runtime.execution.models import ExecutionStrategyResult, StepExecutionOutcome
from app.runtime.execution.sequential import SequentialExecutionStrategy
from app.runtime.execution.strategy import ExecutionStrategy
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.planning.models import ExecutionPlan

_EXECUTION_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "execution"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email", "openai", "langgraph")


class RecordingStepExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._outputs = {"step-a": "A", "step-b": "B"}

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = context
        self.calls.append(step.name)
        return self._outputs[step.name]


class FailingStepExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = context
        self.calls.append(step.name)
        if step.name == "step-b":
            raise RuntimeError("step b failed")
        return "ok"


def _plan(*step_names: str) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-seq",
        agent_id="agent-strategy-1",
        steps=tuple(
            ExecutionStep(name=name, step_type="execute", status="PENDING")
            for name in step_names
        ),
    )


def _step_context() -> StepExecutionContext:
    return StepExecutionContext(
        runtime_context=RuntimeContext(execution_id="exec-strategy-1", agent_id="agent-1"),
        task="strategy task",
    )


def test_sequential_execution_strategy_runs_steps_in_order() -> None:
    strategy = SequentialExecutionStrategy()
    executor = RecordingStepExecutor()

    result = strategy.execute_plan(_plan("step-a", "step-b"), _step_context(), executor)

    assert executor.calls == ["step-a", "step-b"]
    assert result.status == "COMPLETED"
    assert len(result.step_results) == 2


def test_sequential_execution_strategy_aggregates_success_results() -> None:
    strategy = SequentialExecutionStrategy()
    executor = RecordingStepExecutor()

    result = strategy.execute_plan(_plan("step-a", "step-b"), _step_context(), executor)

    assert result.step_results[0].output == "A"
    assert result.step_results[1].output == "B"
    assert all(outcome.step.status == "COMPLETED" for outcome in result.step_results)


def test_sequential_execution_strategy_stops_on_failure() -> None:
    strategy = SequentialExecutionStrategy()
    executor = FailingStepExecutor()

    result = strategy.execute_plan(_plan("step-a", "step-b", "step-c"), _step_context(), executor)

    assert executor.calls == ["step-a", "step-b"]
    assert result.status == "FAILED"
    assert result.error == "step b failed"
    assert len(result.step_results) == 2
    assert result.step_results[-1].step.status == "FAILED"


def test_pipeline_uses_default_sequential_strategy() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-strategy",
        agent_id="agent-strategy-1",
    )
    agent = AgentDefinition(
        id="agent-strategy-1",
        name="strategy-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "default strategy task", context)

    assert result.status == "COMPLETED"
    assert len(result.steps) == 2
    assert result.steps[-1].step_type == "execute"


def test_pipeline_accepts_custom_strategy() -> None:
    class SingleStepStrategy:
        def execute_plan(self, plan, context, step_executor):
            _ = plan
            step = ExecutionStep(name="custom", step_type="execute", status="PENDING")
            output = step_executor.execute_step(step, context)
            return ExecutionStrategyResult(
                step_results=(StepExecutionOutcome(step=step, output=output),),
                status="COMPLETED",
            )

    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        strategy=SingleStepStrategy(),
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-custom-strategy",
        agent_id="agent-strategy-2",
    )
    agent = AgentDefinition(
        id="agent-strategy-2",
        name="custom-strategy-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "custom strategy task", context)

    assert result.status == "COMPLETED"
    assert result.steps[-1].name == "custom"
    assert isinstance(pipeline._strategy, ExecutionStrategy)


def test_execution_strategy_has_no_applications_dependency() -> None:
    for path in _EXECUTION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source.lower(), f"{forbidden!r} found in {path}"
