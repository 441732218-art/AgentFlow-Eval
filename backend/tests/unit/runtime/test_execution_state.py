# AgentFlow Intelligence v2.0 — Execution state tests (Phase 10.7)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.execution.executor import StepExecutionContext
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline, _StateTrackingStepExecutor
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.state.memory_store import InMemoryExecutionStateStore
from app.runtime.state.models import ExecutionState

_STATE_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "state"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email", "openai", "langgraph")


class ProgressRecordingExecutor:
    def __init__(self, state_store: InMemoryExecutionStateStore, execution_id: str) -> None:
        self.state_store = state_store
        self.execution_id = execution_id
        self.observed_steps: list[str | None] = []

    def execute_step(self, step: ExecutionStep, context: StepExecutionContext) -> Any:
        _ = context
        state = self.state_store.get(self.execution_id)
        self.observed_steps.append(state.current_step if state is not None else None)
        return step.name


def _execution_state(execution_id: str = "exec-state-1") -> ExecutionState:
    return ExecutionState(
        execution_id=execution_id,
        agent_id="agent-state-1",
        plan_id="plan-state-1",
        status="RUNNING",
        current_step=None,
        metadata={"task": "state task"},
    )


def _step_context() -> StepExecutionContext:
    return StepExecutionContext(
        runtime_context=RuntimeContext(execution_id="exec-state-1", agent_id="agent-state-1"),
        task="state task",
    )


def test_execution_state_creation() -> None:
    state = _execution_state()

    assert state.execution_id == "exec-state-1"
    assert state.agent_id == "agent-state-1"
    assert state.plan_id == "plan-state-1"
    assert state.status == "RUNNING"
    assert state.current_step is None
    assert state.metadata["task"] == "state task"
    assert state.updated_at >= state.created_at


def test_execution_state_update_returns_new_immutable_instance() -> None:
    state = _execution_state()
    updated = state.with_updates(current_step="execute", status="RUNNING")

    assert updated is not state
    assert updated.current_step == "execute"
    assert state.current_step is None
    assert updated.updated_at >= state.updated_at


def test_in_memory_execution_state_store_crud() -> None:
    store = InMemoryExecutionStateStore()
    state = _execution_state()

    store.create(state)
    assert store.get("exec-state-1") == state

    updated = state.with_updates(current_step="execute")
    store.update(updated)
    assert store.get("exec-state-1") == updated

    store.delete("exec-state-1")
    assert store.get("exec-state-1") is None


def test_in_memory_execution_state_store_rejects_duplicate_create() -> None:
    store = InMemoryExecutionStateStore()
    store.create(_execution_state())

    with pytest.raises(KeyError, match="already exists"):
        store.create(_execution_state())


def test_pipeline_persists_execution_state_on_success() -> None:
    production_runtime = create_production_runtime()
    state_store = InMemoryExecutionStateStore()
    pipeline = AgentExecutionPipeline(production_runtime, state_store=state_store)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-state-success",
        agent_id="agent-state-success",
    )
    agent = AgentDefinition(
        id="agent-state-success",
        name="state-success-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "persist success task", context)
    persisted = state_store.get(result.execution_id)

    assert result.status == "COMPLETED"
    assert persisted is not None
    assert persisted.status == "COMPLETED"
    assert persisted.agent_id == agent.id
    assert persisted.plan_id == result.metadata["plan_id"]
    assert persisted.current_step is None
    assert persisted.metadata["task"] == "persist success task"


def test_pipeline_updates_current_step_during_execution() -> None:
    state_store = InMemoryExecutionStateStore()
    execution_id = "exec-pipeline-state-progress"
    state_store.create(
        ExecutionState(
            execution_id=execution_id,
            agent_id="agent-state-progress",
            plan_id="plan-progress",
            status="RUNNING",
            metadata={"task": "progress task"},
        )
    )
    inner = ProgressRecordingExecutor(state_store, execution_id)
    tracker = _StateTrackingStepExecutor(inner, state_store, execution_id)

    for step_name in ("step-a", "step-b"):
        tracker.execute_step(
            ExecutionStep(name=step_name, step_type="execute", status="RUNNING"),
            _step_context(),
        )

    assert inner.observed_steps == ["step-a", "step-b"]


def test_pipeline_persists_failed_execution_state() -> None:
    production_runtime = create_production_runtime()
    state_store = InMemoryExecutionStateStore()
    pipeline = AgentExecutionPipeline(production_runtime, state_store=state_store)
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
        execution_id="exec-pipeline-state-failed",
        agent_id="agent-state-failed",
    )
    agent = AgentDefinition(
        id="agent-state-failed",
        name="state-failed-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "persist failure task", context)
    persisted = state_store.get(result.execution_id)

    assert result.status == "FAILED"
    assert persisted is not None
    assert persisted.status == "FAILED"
    assert persisted.current_step == "execute"
    assert persisted.metadata["error_message"] == "planned step failed"


def test_pipeline_without_state_store_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-no-state-store",
        agent_id="agent-no-state-store",
    )
    agent = AgentDefinition(
        id="agent-no-state-store",
        name="no-state-store-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "no state store task", context)

    assert result.status == "COMPLETED"
    assert len(result.steps) == 2


def test_execution_state_has_no_forbidden_dependencies() -> None:
    for path in _STATE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source.lower(), f"{forbidden!r} found in {path}"
