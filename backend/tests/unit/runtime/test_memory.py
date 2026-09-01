# AgentFlow Intelligence v2.0 — Runtime Memory unit tests

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.executor import AgentExecutor
from app.runtime.memory import (
    MEMORY_DATA_KEY,
    InMemoryProvider,
    MemoryHook,
    MemoryProvider,
)
from app.runtime.pipeline import ExecutionPipeline


def test_in_memory_provider_set_and_get() -> None:
    provider = InMemoryProvider()

    provider.set("session-1", {"note": "hello"})

    assert provider.get("session-1") == {"note": "hello"}
    assert provider.get("missing") is None


def test_in_memory_provider_delete() -> None:
    provider = InMemoryProvider()
    provider.set("key-a", "value")

    provider.delete("key-a")

    assert provider.get("key-a") is None


def test_in_memory_provider_clear() -> None:
    provider = InMemoryProvider()
    provider.set("key-a", 1)
    provider.set("key-b", 2)

    provider.clear()

    assert provider.get("key-a") is None
    assert provider.get("key-b") is None


def test_memory_hook_before_reads_existing_value() -> None:
    provider = InMemoryProvider()
    provider.set("prior-run", "cached-output")
    hook = MemoryHook(provider)
    context = RuntimeContext(
        execution_id="exec-1",
        agent_id="agent-1",
        metadata={"memory_key": "prior-run"},
    )

    hook.before_execute(context, "task")

    assert context.metadata[MEMORY_DATA_KEY] == "cached-output"


def test_memory_hook_after_updates_agent_memory_by_memory_key() -> None:
    provider = InMemoryProvider()
    hook = MemoryHook(provider)
    context = RuntimeContext(
        execution_id="exec-save",
        agent_id="agent-1",
        metadata={"memory_key": "session-abc"},
    )

    hook.after_execute(context, "pipeline execution completed")

    assert provider.get("session-abc") == "pipeline execution completed"
    assert provider.get("exec-save") is None


def test_memory_hook_after_skips_when_no_memory_key() -> None:
    provider = InMemoryProvider()
    hook = MemoryHook(provider)
    context = RuntimeContext(execution_id="exec-no-key", agent_id="agent-1")

    hook.after_execute(context, "result")

    assert provider.get("exec-no-key") is None


def test_memory_exception_does_not_fail_executor() -> None:
    class BrokenProvider(MemoryProvider):
        def get(self, key: str) -> Any | None:
            raise RuntimeError("memory read failed")

        def set(self, key: str, value: Any) -> None:
            raise RuntimeError("memory write failed")

        def delete(self, key: str) -> None:
            raise RuntimeError("memory delete failed")

        def clear(self) -> None:
            raise RuntimeError("memory clear failed")

    provider = BrokenProvider()
    pipeline = ExecutionPipeline(hooks=[MemoryHook(provider)])
    executor = AgentExecutor(pipeline=pipeline, memory_provider=provider)
    context = RuntimeContext(
        execution_id="exec-broken",
        agent_id="agent-1",
        metadata={"memory_key": "prior-run"},
    )

    result = executor.execute(agent_id="agent-1", task="run", context=context)

    assert result.status == "SUCCESS"


def test_executor_adds_memory_hook_when_provider_given() -> None:
    provider = InMemoryProvider()
    executor = AgentExecutor(memory_provider=provider)
    context = RuntimeContext(
        execution_id="exec-auto",
        agent_id="agent-1",
        metadata={"memory_key": "session-auto"},
    )

    result = executor.execute(agent_id="agent-1", task="run", context=context)

    assert result.status == "SUCCESS"
    assert provider.get("session-auto") == "pipeline execution completed"
    assert provider.get("exec-auto") is None
