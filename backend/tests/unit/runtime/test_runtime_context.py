# AgentFlow Intelligence v2.0 — Runtime context aggregation tests (Phase 10.10)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.checkpoint.manager import CheckpointManager
from app.runtime.checkpoint.memory_store import InMemoryCheckpointStore
from app.runtime.checkpoint.models import Checkpoint
from app.runtime.context.manager import RuntimeContextManager
from app.runtime.context.models import RuntimeContext as AggregatedRuntimeContext
from app.runtime.context.snapshot import RuntimeContextSnapshot, build_snapshot
from app.runtime.context_memory.manager import MemoryContextManager
from app.runtime.context_memory.memory_store import InMemoryMemoryStore
from app.runtime.context_memory.models import MemoryContext
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.state.memory_store import InMemoryExecutionStateStore
from app.runtime.state.models import ExecutionState

_CONTEXT_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "context"
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "openai",
    "langgraph",
    "vector",
    "pgvector",
)


def _aggregated_context(execution_id: str = "exec-ctx-1") -> AggregatedRuntimeContext:
    return AggregatedRuntimeContext(
        execution_id=execution_id,
        agent_id="agent-ctx-1",
        metadata={"task": "context task"},
    )


def _execution_state(execution_id: str = "exec-ctx-1") -> ExecutionState:
    return ExecutionState(
        execution_id=execution_id,
        agent_id="agent-ctx-1",
        plan_id="plan-ctx-1",
        status="RUNNING",
        current_step="execute",
        metadata={"task": "context task"},
    )


def test_runtime_context_creation() -> None:
    context = _aggregated_context()

    assert context.execution_id == "exec-ctx-1"
    assert context.agent_id == "agent-ctx-1"
    assert context.state is None
    assert context.checkpoint is None
    assert context.memory is None
    assert context.metadata["task"] == "context task"


def test_runtime_context_update_returns_new_immutable_instance() -> None:
    context = _aggregated_context()
    state = _execution_state()
    updated = context.with_updates(state=state)

    assert updated is not context
    assert updated.state == state
    assert context.state is None
    assert updated.updated_at >= context.updated_at


def test_runtime_context_snapshot_creation() -> None:
    context = _aggregated_context().with_updates(
        state=_execution_state(),
        checkpoint=Checkpoint(
            checkpoint_id="cp-ctx-1",
            execution_id="exec-ctx-1",
            plan_id="plan-ctx-1",
            step_id="execute",
        ),
        memory=MemoryContext(
            memory_id="mem-ctx-1",
            execution_id="exec-ctx-1",
            agent_id="agent-ctx-1",
            namespace="default",
        ),
    )

    snapshot = build_snapshot(context)

    assert isinstance(snapshot, RuntimeContextSnapshot)
    assert snapshot.execution_id == "exec-ctx-1"
    assert snapshot.status == "RUNNING"
    assert snapshot.current_step == "execute"
    assert snapshot.latest_checkpoint_id == "cp-ctx-1"
    assert snapshot.memory_namespace == "default"


def test_runtime_context_manager_create_and_get() -> None:
    manager = RuntimeContextManager()

    created = manager.create_context(
        execution_id="exec-manager-1",
        agent_id="agent-manager-1",
        metadata={"task": "manager task"},
    )
    loaded = manager.get_context("exec-manager-1")

    assert loaded == created
    assert loaded is not None
    assert loaded.metadata["task"] == "manager task"


def test_runtime_context_manager_update_state() -> None:
    manager = RuntimeContextManager()
    manager.create_context(execution_id="exec-state-1", agent_id="agent-state-1")
    state = _execution_state("exec-state-1")

    updated = manager.update_state("exec-state-1", state)

    assert updated.state == state
    assert manager.get_context("exec-state-1") == updated


def test_runtime_context_manager_update_checkpoint() -> None:
    manager = RuntimeContextManager()
    manager.create_context(execution_id="exec-cp-1", agent_id="agent-cp-1")
    checkpoint = Checkpoint(
        checkpoint_id="cp-manager-1",
        execution_id="exec-cp-1",
        plan_id="plan-cp-1",
    )

    updated = manager.update_checkpoint("exec-cp-1", checkpoint)

    assert updated.checkpoint == checkpoint
    assert manager.get_context("exec-cp-1") == updated


def test_runtime_context_manager_update_memory() -> None:
    manager = RuntimeContextManager()
    manager.create_context(execution_id="exec-mem-1", agent_id="agent-mem-1")
    memory = MemoryContext(
        memory_id="mem-manager-1",
        execution_id="exec-mem-1",
        agent_id="agent-mem-1",
        namespace="default",
        data={"task": "memory task"},
    )

    updated = manager.update_memory("exec-mem-1", memory)

    assert updated.memory == memory
    assert manager.get_context("exec-mem-1") == updated


def test_pipeline_integrates_runtime_context_manager() -> None:
    production_runtime = create_production_runtime()
    state_store = InMemoryExecutionStateStore()
    checkpoint_store = InMemoryCheckpointStore()
    memory_store = InMemoryMemoryStore()
    runtime_context_manager = RuntimeContextManager()
    pipeline = AgentExecutionPipeline(
        production_runtime,
        state_store=state_store,
        checkpoint_store=checkpoint_store,
        memory_manager=MemoryContextManager(memory_store),
        runtime_context_manager=runtime_context_manager,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-runtime-context",
        agent_id="agent-runtime-context",
    )
    agent = AgentDefinition(
        id="agent-runtime-context",
        name="runtime-context-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "runtime context task", context)
    aggregated = runtime_context_manager.get_context(result.execution_id)
    snapshot = runtime_context_manager.snapshot(result.execution_id)

    assert result.status == "COMPLETED"
    assert aggregated is not None
    assert aggregated.state is not None
    assert aggregated.state.status == "COMPLETED"
    assert aggregated.checkpoint is not None
    assert aggregated.memory is not None
    assert snapshot.status == "COMPLETED"
    assert snapshot.latest_checkpoint_id == aggregated.checkpoint.checkpoint_id
    assert snapshot.memory_namespace == "default"


def test_pipeline_without_runtime_context_manager_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-no-runtime-context-manager",
        agent_id="agent-no-runtime-context-manager",
    )
    agent = AgentDefinition(
        id="agent-no-runtime-context-manager",
        name="no-runtime-context-manager-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "no runtime context manager task", context)

    assert result.status == "COMPLETED"
    assert len(result.steps) == 2


def test_runtime_context_has_no_forbidden_dependencies() -> None:
    for path in _CONTEXT_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
