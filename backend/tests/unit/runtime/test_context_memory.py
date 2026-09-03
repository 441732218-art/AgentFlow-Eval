# AgentFlow Intelligence v2.0 — Runtime memory context tests (Phase 10.9)

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context_memory.manager import MemoryContextManager
from app.runtime.context_memory.memory_store import InMemoryMemoryStore
from app.runtime.context_memory.models import MemoryContext
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

_CONTEXT_MEMORY_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "context_memory"
)
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.runtime.memory",
    "app.api",
    "app.service",
    "app.tracing",
    "trade",
    "CRM",
    "Email",
    "openai",
    "langgraph",
    "vector",
    "pgvector",
)


def _memory_context(memory_id: str = "mem-1") -> MemoryContext:
    return MemoryContext(
        memory_id=memory_id,
        execution_id="exec-mem-1",
        agent_id="agent-mem-1",
        namespace="default",
        data={"task": "memory task"},
    )


def test_memory_context_creation() -> None:
    context = _memory_context()

    assert context.memory_id == "mem-1"
    assert context.execution_id == "exec-mem-1"
    assert context.agent_id == "agent-mem-1"
    assert context.namespace == "default"
    assert context.data["task"] == "memory task"
    assert context.updated_at >= context.created_at


def test_memory_context_update_returns_new_immutable_instance() -> None:
    context = _memory_context()
    updated = context.with_updates(data={**context.data, "status": "RUNNING"})

    assert updated is not context
    assert updated.data["status"] == "RUNNING"
    assert "status" not in context.data
    assert updated.updated_at >= context.updated_at


def test_in_memory_memory_store_crud_and_list() -> None:
    store = InMemoryMemoryStore()
    first = _memory_context("mem-a")
    second = MemoryContext(
        memory_id="mem-b",
        execution_id="exec-mem-2",
        agent_id="agent-mem-2",
        namespace="session",
        data={"task": "other task"},
    )

    store.create(first)
    store.create(second)

    assert store.get("mem-a") == first
    updated = first.with_updates(data={**first.data, "status": "COMPLETED"})
    store.update(updated)
    assert store.get("mem-a") == updated

    listed = store.list(agent_id="agent-mem-2", namespace="session")
    assert [item.memory_id for item in listed] == ["mem-b"]

    store.delete("mem-a")
    assert store.get("mem-a") is None


def test_in_memory_memory_store_is_thread_safe() -> None:
    store = InMemoryMemoryStore()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            context = MemoryContext(
                memory_id=f"mem-thread-{index}",
                execution_id=f"exec-thread-{index}",
                agent_id=f"agent-thread-{index}",
                namespace="default",
                data={"index": index},
            )
            store.create(context)
            loaded = store.get(context.memory_id)
            assert loaded is not None
            store.update(loaded.with_updates(data={**loaded.data, "seen": True}))
            store.list(execution_id=context.execution_id)
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(store.list()) == 8


def test_memory_context_manager_load_update_and_persist() -> None:
    store = InMemoryMemoryStore()
    manager = MemoryContextManager(store)

    loaded = manager.load_context(
        execution_id="exec-manager-1",
        agent_id="agent-manager-1",
    )
    updated = manager.update_context(loaded, {"task": "manager task", "status": "RUNNING"})
    persisted = manager.persist_context(updated)

    assert persisted.memory_id == loaded.memory_id
    stored = store.get(persisted.memory_id)
    assert stored is not None
    assert stored.data["task"] == "manager task"
    assert stored.data["status"] == "RUNNING"

    reloaded = manager.load_context(
        execution_id="exec-manager-1",
        agent_id="agent-manager-1",
    )
    assert reloaded.memory_id == loaded.memory_id
    assert reloaded.data["task"] == "manager task"


def test_pipeline_persists_memory_context_on_success() -> None:
    production_runtime = create_production_runtime()
    memory_store = InMemoryMemoryStore()
    memory_manager = MemoryContextManager(memory_store)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        memory_manager=memory_manager,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-pipeline-memory-success",
        agent_id="agent-memory-success",
    )
    agent = AgentDefinition(
        id="agent-memory-success",
        name="memory-success-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "memory success task", context)
    stored_records = memory_store.list(
        execution_id=result.execution_id,
        agent_id=agent.id,
    )

    assert result.status == "COMPLETED"
    assert len(stored_records) == 1
    assert stored_records[0].data["task"] == "memory success task"
    assert stored_records[0].data["status"] == "COMPLETED"
    assert stored_records[0].data["plan_id"] == result.metadata["plan_id"]


def test_pipeline_without_memory_manager_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-no-memory-manager",
        agent_id="agent-no-memory-manager",
    )
    agent = AgentDefinition(
        id="agent-no-memory-manager",
        name="no-memory-manager-agent",
        tool_names=[],
    )

    result = pipeline.run(agent, "no memory manager task", context)

    assert result.status == "COMPLETED"
    assert len(result.steps) == 2


def test_context_memory_has_no_forbidden_dependencies() -> None:
    for path in _CONTEXT_MEMORY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
