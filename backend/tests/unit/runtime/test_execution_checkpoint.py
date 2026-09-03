# AgentFlow Intelligence v2.0 — Execution checkpoint tests (Phase 10.8)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.checkpoint.manager import CheckpointManager
from app.runtime.checkpoint.memory_store import InMemoryCheckpointStore
from app.runtime.checkpoint.models import Checkpoint
from app.runtime.context import RuntimeContext
from app.runtime.execution.executor import StepExecutionContext
from app.runtime.execution.models import ExecutionStrategyResult, StepExecutionOutcome
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline, _CheckpointTrackingStepExecutor
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.pipeline.steps import complete_step, create_step
from app.runtime.planning.models import ExecutionPlan
from app.runtime.state.models import ExecutionState

_CHECKPOINT_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "checkpoint"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email", "openai", "langgraph")


class RecordingStepExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = context
        self.calls.append(step.name)
        return step.name


class TwoStepPlanner:
    def create_plan(self, agent_definition, task, context):
        _ = task, context
        return ExecutionPlan(
            plan_id="plan-two-step",
            agent_id=agent_definition.id,
            steps=(
                ExecutionStep(name="step-a", step_type="execute", status="PENDING"),
                ExecutionStep(name="step-b", step_type="execute", status="PENDING"),
            ),
        )


class RecordingStrategy:
    def __init__(self) -> None:
        self.executed_steps: list[str] = []

    def execute_plan(self, plan, context, step_executor):
        outcomes: list[StepExecutionOutcome] = []
        for planned_step in plan.steps:
            active_step = create_step(planned_step.name, planned_step.step_type)
            output = step_executor.execute_step(active_step, context)
            complete_step(active_step)
            self.executed_steps.append(planned_step.name)
            outcomes.append(StepExecutionOutcome(step=active_step, output=output))
        return ExecutionStrategyResult(step_results=tuple(outcomes), status="COMPLETED")


def _checkpoint(checkpoint_id: str = "cp-1") -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        execution_id="exec-cp-1",
        plan_id="plan-cp-1",
        step_id="step-a",
        state_snapshot={
            "agent_id": "agent-cp-1",
            "task": "checkpoint task",
            "completed_steps": [],
            "status": "RUNNING",
        },
        metadata={"phase": "test"},
    )


def _step_context() -> StepExecutionContext:
    return StepExecutionContext(
        runtime_context=RuntimeContext(execution_id="exec-cp-1", agent_id="agent-cp-1"),
        task="checkpoint task",
    )


def test_checkpoint_creation() -> None:
    checkpoint = _checkpoint()

    assert checkpoint.checkpoint_id == "cp-1"
    assert checkpoint.execution_id == "exec-cp-1"
    assert checkpoint.plan_id == "plan-cp-1"
    assert checkpoint.step_id == "step-a"
    assert checkpoint.state_snapshot["task"] == "checkpoint task"
    assert checkpoint.metadata["phase"] == "test"


def test_checkpoint_from_execution_state() -> None:
    state = ExecutionState(
        execution_id="exec-cp-2",
        agent_id="agent-cp-2",
        plan_id="plan-cp-2",
        status="RUNNING",
        current_step="step-a",
        metadata={"task": "state task", "completed_steps": ["prepare"]},
    )

    checkpoint = Checkpoint.from_execution_state(
        checkpoint_id="cp-2",
        state=state,
        step_id="step-a",
        metadata={"phase": "from_state"},
    )

    assert checkpoint.execution_id == "exec-cp-2"
    assert checkpoint.state_snapshot["completed_steps"] == ["prepare"]
    assert checkpoint.metadata["phase"] == "from_state"


def test_in_memory_checkpoint_store_save_get_latest_and_list() -> None:
    store = InMemoryCheckpointStore()
    first = _checkpoint("cp-a")
    second = Checkpoint(
        checkpoint_id="cp-b",
        execution_id="exec-cp-1",
        plan_id="plan-cp-1",
        step_id="step-b",
        state_snapshot={"completed_steps": ["step-a"]},
    )

    store.save(first)
    store.save(second)

    assert store.get("cp-a") == first
    assert store.get_latest("exec-cp-1") == second
    assert [item.checkpoint_id for item in store.list_by_execution("exec-cp-1")] == [
        "cp-a",
        "cp-b",
    ]

    store.delete("cp-a")
    assert store.get("cp-a") is None


def test_checkpoint_manager_plan_for_resume_skips_completed_steps() -> None:
    manager = CheckpointManager(InMemoryCheckpointStore())
    plan = ExecutionPlan(
        plan_id="plan-resume",
        agent_id="agent-resume",
        steps=(
            ExecutionStep(name="step-a", step_type="execute", status="PENDING"),
            ExecutionStep(name="step-b", step_type="execute", status="PENDING"),
            ExecutionStep(name="step-c", step_type="execute", status="PENDING"),
        ),
    )
    checkpoint = manager.save_checkpoint(
        execution_id="exec-resume",
        plan_id="plan-resume",
        step_id="step-b",
        state_snapshot={"completed_steps": ["step-a"]},
    )

    resumed_plan = manager.plan_for_resume(plan, checkpoint)

    assert [step.name for step in resumed_plan.steps] == ["step-b", "step-c"]


def test_checkpoint_tracking_executor_persists_step_level_checkpoints() -> None:
    store = InMemoryCheckpointStore()
    manager = CheckpointManager(store)
    completed_steps: list[str] = []
    tracker = _CheckpointTrackingStepExecutor(
        RecordingStepExecutor(),
        manager,
        execution_id="exec-step-cp",
        plan_id="plan-step-cp",
        agent_id="agent-step-cp",
        task="step checkpoint task",
        completed_steps=completed_steps,
    )

    tracker.execute_step(
        ExecutionStep(name="step-a", step_type="execute", status="RUNNING"),
        _step_context(),
    )

    checkpoints = store.list_by_execution("exec-step-cp")
    assert len(checkpoints) == 2
    assert checkpoints[0].metadata["phase"] == "before_step"
    assert checkpoints[1].metadata["phase"] == "after_step"
    assert checkpoints[1].state_snapshot["completed_steps"] == ["step-a"]


def test_pipeline_persists_execution_checkpoints_on_success() -> None:
    production_runtime = create_production_runtime()
    checkpoint_store = InMemoryCheckpointStore()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        checkpoint_store=checkpoint_store,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-checkpoint-success",
        agent_id="agent-checkpoint-success",
    )
    agent = AgentDefinition(
        id="agent-checkpoint-success",
        name="checkpoint-success-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "checkpoint success task", context)
    latest = CheckpointManager(checkpoint_store).get_resume_point(result.execution_id)

    assert result.status == "COMPLETED"
    assert latest is not None
    assert latest.state_snapshot["status"] == "COMPLETED"
    assert latest.metadata["phase"] == "execution_completed"


def test_pipeline_resume_skips_completed_steps() -> None:
    production_runtime = create_production_runtime()
    checkpoint_store = InMemoryCheckpointStore()
    manager = CheckpointManager(checkpoint_store)
    strategy = RecordingStrategy()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        planner=TwoStepPlanner(),
        strategy=strategy,
        checkpoint_store=checkpoint_store,
    )
    pipeline._execution_pipeline = type(
        "StubPipeline",
        (),
        {"run": staticmethod(lambda runtime_context, task: "ok")},
    )()
    execution_id = "exec-pipeline-checkpoint-resume"
    checkpoint = manager.save_checkpoint(
        execution_id=execution_id,
        plan_id="plan-two-step",
        step_id="step-a",
        state_snapshot={
            "agent_id": "agent-checkpoint-resume",
            "task": "resume task",
            "completed_steps": ["step-a"],
            "status": "RUNNING",
        },
        metadata={"phase": "manual_resume_point"},
    )
    context = create_execution_context(
        production_runtime,
        execution_id=execution_id,
        agent_id="agent-checkpoint-resume",
    )
    agent = AgentDefinition(
        id="agent-checkpoint-resume",
        name="checkpoint-resume-agent",
        tool_names=[],
    )

    result = pipeline.run(
        agent,
        "resume task",
        context,
        resume_from_checkpoint_id=checkpoint.checkpoint_id,
    )

    assert result.status == "COMPLETED"
    assert strategy.executed_steps == ["step-b"]


def test_pipeline_persists_failed_execution_checkpoint() -> None:
    production_runtime = create_production_runtime()
    checkpoint_store = InMemoryCheckpointStore()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        checkpoint_store=checkpoint_store,
    )
    pipeline._execution_pipeline = type(
        "FailingPipeline",
        (),
        {
            "run": staticmethod(
                lambda runtime_context, task: (_ for _ in ()).throw(
                    RuntimeError("planned step failed")
                )
            )
        },
    )()
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-checkpoint-failed",
        agent_id="agent-checkpoint-failed",
    )
    agent = AgentDefinition(
        id="agent-checkpoint-failed",
        name="checkpoint-failed-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "checkpoint failure task", context)
    latest = CheckpointManager(checkpoint_store).get_resume_point(result.execution_id)

    assert result.status == "FAILED"
    assert latest is not None
    assert latest.state_snapshot["status"] == "FAILED"
    assert latest.metadata["phase"] == "execution_failed"


def test_pipeline_without_checkpoint_store_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-no-checkpoint-store",
        agent_id="agent-no-checkpoint-store",
    )
    agent = AgentDefinition(
        id="agent-no-checkpoint-store",
        name="no-checkpoint-store-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "no checkpoint store task", context)

    assert result.status == "COMPLETED"
    assert len(result.steps) == 2


def test_pipeline_resume_requires_checkpoint_store() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-resume-no-store",
        agent_id="agent-resume-no-store",
    )
    agent = AgentDefinition(
        id="agent-resume-no-store",
        name="resume-no-store-agent",
        tool_names=[],
    )

    with pytest.raises(RuntimeError, match="checkpoint store is required"):
        pipeline.run(
            agent,
            "resume task",
            context,
            resume_from_checkpoint_id="missing-checkpoint",
        )


def test_execution_checkpoint_has_no_forbidden_dependencies() -> None:
    for path in _CHECKPOINT_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source.lower(), f"{forbidden!r} found in {path}"
