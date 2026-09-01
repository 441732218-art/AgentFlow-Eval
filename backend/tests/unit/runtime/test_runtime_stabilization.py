# AgentFlow Intelligence v2.0 — Runtime stabilization tests (Phase 7.1.5)

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.runtime.context import RuntimeContext
from app.runtime.execution import InMemoryExecutionStore
from app.runtime.executor import AgentExecutor
from app.runtime.memory import MEMORY_DATA_KEY, InMemoryProvider
from app.runtime.memory.hook import MemoryHook
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.service import RuntimeService


def _service_with_memory() -> tuple[RuntimeService, InMemoryProvider, InMemoryExecutionStore]:
    provider = InMemoryProvider()
    store = InMemoryExecutionStore()
    executor = AgentExecutor(memory_provider=provider)
    service = RuntimeService(executor=executor, execution_store=store)
    return service, provider, store


def test_memory_round_trip_across_runtime_service_execute_calls() -> None:
    service, provider, _store = _service_with_memory()
    memory_reads: list[object | None] = []
    original_before = MemoryHook.before_execute

    def capture_before_execute(
        hook_self: MemoryHook,
        context: RuntimeContext,
        task: str,
    ) -> None:
        original_before(hook_self, context, task)
        if task == "second task":
            memory_reads.append(context.metadata.get(MEMORY_DATA_KEY))

    with patch.object(MemoryHook, "before_execute", capture_before_execute):
        first = service.execute(
            agent_id="sales-agent",
            task="first task",
            context=RuntimeContext(
                execution_id="exec-round-1",
                agent_id="sales-agent",
                metadata={"memory_key": "session-001"},
            ),
        )
        second = service.execute(
            agent_id="sales-agent",
            task="second task",
            context=RuntimeContext(
                execution_id="exec-round-2",
                agent_id="sales-agent",
                metadata={"memory_key": "session-001"},
            ),
        )

    assert first.status == "SUCCESS"
    assert second.status == "SUCCESS"
    assert provider.get("session-001") == "pipeline execution completed"
    assert len(memory_reads) == 1
    assert memory_reads[0] == "pipeline execution completed"


def test_failed_execution_does_not_corrupt_memory() -> None:
    provider = InMemoryProvider()
    failing_pipeline = MagicMock(spec=ExecutionPipeline)
    failing_pipeline.run.side_effect = RuntimeError("forced failure")
    executor = AgentExecutor(pipeline=failing_pipeline, memory_provider=provider)
    service = RuntimeService(executor=executor)

    dto = service.execute(
        agent_id="test-agent",
        task="failure task",
        context=RuntimeContext(
            execution_id="exec-fail-mem",
            agent_id="test-agent",
            metadata={"memory_key": "session-failure"},
        ),
    )

    assert dto.status == "FAILED"
    assert dto.error == "forced failure"
    assert provider.get("session-failure") is None


def test_failed_execution_does_not_overwrite_existing_session_memory() -> None:
    provider = InMemoryProvider()
    provider.set("session-failure", {"state": "prior"})
    failing_pipeline = MagicMock(spec=ExecutionPipeline)
    failing_pipeline.run.side_effect = RuntimeError("forced failure")
    executor = AgentExecutor(pipeline=failing_pipeline, memory_provider=provider)
    service = RuntimeService(executor=executor)

    dto = service.execute(
        agent_id="test-agent",
        task="failure task",
        context=RuntimeContext(
            execution_id="exec-fail-mem-2",
            agent_id="test-agent",
            metadata={"memory_key": "session-failure"},
        ),
    )

    assert dto.status == "FAILED"
    assert provider.get("session-failure") == {"state": "prior"}


def test_runtime_service_persists_failed_execution() -> None:
    store = InMemoryExecutionStore()
    failing_pipeline = MagicMock(spec=ExecutionPipeline)
    failing_pipeline.run.side_effect = RuntimeError("executor failed")
    executor = AgentExecutor(pipeline=failing_pipeline)
    service = RuntimeService(executor=executor, execution_store=store)

    dto = service.execute(
        agent_id="test-agent",
        task="failure task",
        context=RuntimeContext(
            execution_id="exec-persist-fail",
            agent_id="test-agent",
        ),
    )

    assert dto.execution_id == "exec-persist-fail"
    assert dto.status == "FAILED"
    assert dto.error == "executor failed"
    assert dto.output is None

    record = store.get("exec-persist-fail")
    assert record is not None
    assert record.execution_id == "exec-persist-fail"
    assert record.status == "FAILED"
    assert record.error == "executor failed"
    assert record.output is None
