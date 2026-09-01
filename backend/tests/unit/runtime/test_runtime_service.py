# AgentFlow Intelligence v2.0 — RuntimeService unit tests

from __future__ import annotations

from unittest.mock import patch

from app.runtime.context import RuntimeContext
from app.runtime.execution import InMemoryExecutionStore
from app.runtime.service import ExecutionResponseDTO, RuntimeService


def test_runtime_service_execute_success() -> None:
    service = RuntimeService()

    dto = service.execute(agent_id="agent-1", task="hello")

    assert isinstance(dto, ExecutionResponseDTO)
    assert dto.status == "SUCCESS"
    assert dto.output == "pipeline execution completed"
    assert dto.error is None
    assert dto.execution_id


def test_runtime_service_creates_execution_record() -> None:
    store = InMemoryExecutionStore()
    service = RuntimeService(execution_store=store)

    dto = service.execute(agent_id="agent-1", task="persist me")
    record = store.get(dto.execution_id)

    assert record is not None
    assert record.agent_id == "agent-1"
    assert record.status == "SUCCESS"
    assert record.output == "pipeline execution completed"
    assert record.trace_reference == dto.execution_id


def test_runtime_service_execution_id_consistent_with_context() -> None:
    store = InMemoryExecutionStore()
    service = RuntimeService(execution_store=store)
    context = RuntimeContext(
        execution_id="exec-fixed-42",
        agent_id="agent-1",
    )

    dto = service.execute(agent_id="agent-1", task="run", context=context)
    record = store.get("exec-fixed-42")

    assert dto.execution_id == "exec-fixed-42"
    assert record is not None
    assert record.execution_id == "exec-fixed-42"


def test_runtime_service_failure_status_persisted() -> None:
    store = InMemoryExecutionStore()
    service = RuntimeService(execution_store=store)

    with patch(
        "app.runtime.executor.executor.RuntimeContext",
        side_effect=RuntimeError("boom"),
    ):
        dto = service.execute(agent_id="agent-fail", task="run")

    assert dto.status == "FAILED"
    assert dto.error == "boom"
    assert dto.output is None

    record = store.get(dto.execution_id)
    assert record is not None
    assert record.status == "FAILED"
    assert record.error == "boom"


def test_runtime_service_dto_does_not_expose_internal_result_type() -> None:
    service = RuntimeService()

    dto = service.execute(agent_id="agent-1", task="dto check")

    assert type(dto).__name__ == "ExecutionResponseDTO"
    assert not hasattr(dto, "agent_id")
