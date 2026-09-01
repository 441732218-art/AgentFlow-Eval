# AgentFlow Intelligence v2.0 — Execution Pipeline unit tests

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.runtime.context import RuntimeContext
from app.runtime.executor import AgentExecutor
from app.runtime.pipeline import ExecutionHook, ExecutionPipeline


class RecordingHook(ExecutionHook):
    """Test hook that records lifecycle calls."""

    def __init__(self) -> None:
        self.before_calls: list[tuple[RuntimeContext, str]] = []
        self.after_calls: list[tuple[RuntimeContext, Any]] = []

    def before_execute(self, context: RuntimeContext, task: str) -> None:
        self.before_calls.append((context, task))

    def after_execute(self, context: RuntimeContext, result: Any) -> None:
        self.after_calls.append((context, result))


def test_pipeline_run_success() -> None:
    pipeline = ExecutionPipeline()
    context = RuntimeContext(execution_id="exec-1", agent_id="agent-1")

    result = pipeline.run(context, "do work")

    assert result == "pipeline execution completed"


def test_hook_before_is_called() -> None:
    hook = RecordingHook()
    pipeline = ExecutionPipeline(hooks=[hook])
    context = RuntimeContext(execution_id="exec-2", agent_id="agent-1")

    pipeline.run(context, "task-a")

    assert len(hook.before_calls) == 1
    assert hook.before_calls[0] == (context, "task-a")


def test_hook_after_is_called() -> None:
    hook = RecordingHook()
    pipeline = ExecutionPipeline(hooks=[hook])
    context = RuntimeContext(execution_id="exec-3", agent_id="agent-1")

    pipeline.run(context, "task-b")

    assert len(hook.after_calls) == 1
    called_context, called_result = hook.after_calls[0]
    assert called_context is context
    assert called_result == "pipeline execution completed"


def test_executor_uses_pipeline() -> None:
    pipeline = MagicMock(spec=ExecutionPipeline)
    pipeline.run.return_value = "pipeline execution completed"
    executor = AgentExecutor(pipeline=pipeline)

    result = executor.execute(agent_id="agent-1", task="hello")

    pipeline.run.assert_called_once()
    call_context, call_task = pipeline.run.call_args[0]
    assert call_context.agent_id == "agent-1"
    assert call_task == "hello"
    assert result.status == "SUCCESS"
    assert result.output == "pipeline execution completed"


def test_pipeline_exception_handled_by_executor() -> None:
    pipeline = MagicMock(spec=ExecutionPipeline)
    pipeline.run.side_effect = RuntimeError("pipeline failed")
    executor = AgentExecutor(pipeline=pipeline)

    result = executor.execute(agent_id="agent-err", task="fail")

    assert result.status == "FAILED"
    assert result.error == "pipeline failed"
    assert result.output is None


def test_pipeline_execute_step_exception_propagates() -> None:
    pipeline = ExecutionPipeline()

    with patch.object(pipeline, "_execute_step", side_effect=ValueError("step failed")):
        with pytest.raises(ValueError, match="step failed"):
            pipeline.run(
                RuntimeContext(execution_id="exec-4", agent_id="agent-1"),
                "task",
            )
