# AgentFlow Intelligence v2.0 — Execution control tests (Phase 10.6)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.execution.control import ExecutionController
from app.runtime.execution.executor import StepExecutionContext, StepExecutor
from app.runtime.execution.failure import DefaultFailurePolicy
from app.runtime.execution.retry import DefaultRetryPolicy
from app.runtime.execution.sequential import SequentialExecutionStrategy
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.planning.models import ExecutionPlan

_EXECUTION_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "execution"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email", "openai", "langgraph")


class RetryThenSucceedExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = step, context
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient failure")
        return "recovered"


class AlwaysFailingExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = step, context
        self.calls += 1
        raise RuntimeError("persistent failure")


class SelectiveFailureExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = context
        self.calls.append(step.name)
        if step.name == "step-b":
            raise RuntimeError("step b failed")
        return f"{step.name}-ok"


class RecordingStepExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = context
        self.calls.append(step.name)
        return step.name


def _plan(*step_names: str) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-control",
        agent_id="agent-control-1",
        steps=tuple(
            ExecutionStep(name=name, step_type="execute", status="PENDING")
            for name in step_names
        ),
    )


def _step(name: str = "step-a") -> ExecutionStep:
    return ExecutionStep(name=name, step_type="execute", status="RUNNING")


def _step_context() -> StepExecutionContext:
    return StepExecutionContext(
        runtime_context=RuntimeContext(execution_id="exec-control-1", agent_id="agent-1"),
        task="control task",
    )


def test_execution_controller_retries_until_success() -> None:
    controller = ExecutionController(retry_policy=DefaultRetryPolicy(max_attempts=3))
    executor = RetryThenSucceedExecutor()

    outcome = controller.execute_step(_step(), _step_context(), executor)

    assert outcome.success is True
    assert outcome.output == "recovered"
    assert outcome.attempts == 2
    assert executor.calls == 2


def test_execution_controller_stops_when_retry_exhausted() -> None:
    controller = ExecutionController(retry_policy=DefaultRetryPolicy(max_attempts=2))
    executor = AlwaysFailingExecutor()

    outcome = controller.execute_step(_step(), _step_context(), executor)

    assert outcome.success is False
    assert outcome.error == "persistent failure"
    assert outcome.attempts == 2
    assert outcome.stop_plan is True
    assert executor.calls == 2


def test_failure_policy_stop_halts_plan_execution() -> None:
    strategy = SequentialExecutionStrategy(
        controller=ExecutionController(
            failure_policy=DefaultFailurePolicy(action="STOP"),
        )
    )
    executor = SelectiveFailureExecutor()

    result = strategy.execute_plan(_plan("step-a", "step-b", "step-c"), _step_context(), executor)

    assert executor.calls == ["step-a", "step-b"]
    assert result.status == "FAILED"
    assert result.error == "step b failed"
    assert len(result.step_results) == 2
    assert result.step_results[-1].step.status == "FAILED"


def test_failure_policy_continue_runs_remaining_steps() -> None:
    strategy = SequentialExecutionStrategy(
        controller=ExecutionController(
            failure_policy=DefaultFailurePolicy(action="CONTINUE"),
        )
    )
    executor = SelectiveFailureExecutor()

    result = strategy.execute_plan(_plan("step-a", "step-b", "step-c"), _step_context(), executor)

    assert executor.calls == ["step-a", "step-b", "step-c"]
    assert result.status == "COMPLETED"
    assert result.error == "step b failed"
    assert len(result.step_results) == 3
    assert result.step_results[0].step.status == "COMPLETED"
    assert result.step_results[1].step.status == "FAILED"
    assert result.step_results[2].step.status == "COMPLETED"


def test_default_execution_control_preserves_existing_behavior() -> None:
    strategy = SequentialExecutionStrategy()
    executor = RecordingStepExecutor()

    result = strategy.execute_plan(_plan("step-a", "step-b"), _step_context(), executor)

    assert executor.calls == ["step-a", "step-b"]
    assert result.status == "COMPLETED"
    assert len(result.step_results) == 2

    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-default-control",
        agent_id="agent-control-default",
    )
    agent = AgentDefinition(
        id="agent-control-default",
        name="default-control-agent",
        tool_names=[],
    )

    pipeline_result = pipeline.run(agent, "default control task", context)

    assert pipeline_result.status == "COMPLETED"
    assert len(pipeline_result.steps) == 2


def test_execution_control_has_no_applications_dependency() -> None:
    for path in _EXECUTION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source.lower(), f"{forbidden!r} found in {path}"
