# AgentFlow Intelligence v2.0 — Agent Executor unit tests

from __future__ import annotations

from unittest.mock import patch

from app.runtime.context import RuntimeContext
from app.runtime.executor import AgentExecutor, ExecutionResult
from app.runtime.tools import ToolRegistry


def test_execute_success() -> None:
    executor = AgentExecutor()
    result = executor.execute(agent_id="agent-1", task="hello")

    assert isinstance(result, ExecutionResult)
    assert result.status == "SUCCESS"
    assert result.agent_id == "agent-1"
    assert result.output == "pipeline execution completed"
    assert result.error is None
    assert result.execution_id


def test_execute_auto_creates_context() -> None:
    executor = AgentExecutor()
    result = executor.execute(agent_id="agent-auto", task="run")

    assert result.status == "SUCCESS"
    assert len(result.execution_id) == 32


def test_execute_preserves_provided_context_execution_id() -> None:
    executor = AgentExecutor()
    context = RuntimeContext(
        execution_id="exec-fixed-001",
        agent_id="agent-1",
        metadata={"source": "test"},
    )

    result = executor.execute(agent_id="agent-1", task="run", context=context)

    assert result.execution_id == "exec-fixed-001"
    assert result.status == "SUCCESS"


def test_execute_returns_failed_on_exception() -> None:
    executor = AgentExecutor()

    with patch(
        "app.runtime.executor.executor.RuntimeContext",
        side_effect=RuntimeError("boom"),
    ):
        result = executor.execute(agent_id="agent-fail", task="run")

    assert result.status == "FAILED"
    assert result.output is None
    assert result.error == "boom"
    assert result.agent_id == "agent-fail"
    assert result.execution_id


def test_tool_registry_can_be_injected() -> None:
    registry = ToolRegistry()
    executor = AgentExecutor(tool_registry=registry)

    assert executor.tool_registry is registry

    result = executor.execute(agent_id="agent-tools", task="noop")
    assert result.status == "SUCCESS"
