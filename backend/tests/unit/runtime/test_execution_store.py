# AgentFlow Intelligence v2.0 — ExecutionStore unit tests

from __future__ import annotations

import pytest

from app.runtime.execution import ExecutionRecord, InMemoryExecutionStore


def _record(
    execution_id: str = "exec-1",
    status: str = "SUCCESS",
    output: str | None = "done",
) -> ExecutionRecord:
    return ExecutionRecord(
        execution_id=execution_id,
        agent_id="agent-1",
        status=status,
        output=output,
        error=None,
        trace_reference=execution_id,
    )


def test_execution_store_save_and_get() -> None:
    store = InMemoryExecutionStore()
    record = _record()

    store.save(record)
    fetched = store.get("exec-1")

    assert fetched is not None
    assert fetched.execution_id == "exec-1"
    assert fetched.status == "SUCCESS"
    assert fetched.output == "done"
    assert fetched.trace_reference == "exec-1"


def test_execution_store_get_missing_returns_none() -> None:
    store = InMemoryExecutionStore()

    assert store.get("missing") is None


def test_execution_store_update_status() -> None:
    store = InMemoryExecutionStore()
    store.save(_record(status="RUNNING"))

    store.update_status("exec-1", "FAILED")
    fetched = store.get("exec-1")

    assert fetched is not None
    assert fetched.status == "FAILED"


def test_execution_store_update_status_missing_raises() -> None:
    store = InMemoryExecutionStore()

    with pytest.raises(KeyError, match="Execution not found"):
        store.update_status("missing", "FAILED")


def test_execution_store_save_preserves_created_at() -> None:
    store = InMemoryExecutionStore()
    first = _record()
    store.save(first)
    created_at = store.get("exec-1").created_at  # type: ignore[union-attr]

    updated = _record(output="updated")
    store.save(updated)
    fetched = store.get("exec-1")

    assert fetched is not None
    assert fetched.created_at == created_at
    assert fetched.output == "updated"
