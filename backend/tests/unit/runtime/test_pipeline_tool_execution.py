# AgentFlow Intelligence v2.0 — Pipeline tool execution tests (Phase 8.4)

from __future__ import annotations

from typing import Any

import pytest

from app.runtime.context import RuntimeContext
from app.runtime.executor import AgentExecutor, attach_tool_request
from app.runtime.executor.context_fields import get_tool_definition
from app.runtime.memory import InMemoryProvider, MEMORY_DATA_KEY
from app.runtime.memory.hook import MemoryHook
from app.runtime.pipeline import ExecutionHook, ExecutionPipeline
from app.runtime.pipeline.tool_step import ToolExecutionEngineRequiredError
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.factory import (
    create_default_tool_execution_engine,
    create_tool_execution_engine,
)
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.remote_client import InMemoryRemoteClient
from app.runtime.tracing import TraceHook
from app.runtime.tracing.trace_hook import RUNTIME_TRACE_KEY


class RecordingHook(ExecutionHook):
    def __init__(self) -> None:
        self.events: list[str] = []

    def before_execute(self, context: RuntimeContext, task: str) -> None:
        _ = context, task
        self.events.append("before")

    def after_execute(self, context: RuntimeContext, result: Any) -> None:
        _ = context, result
        self.events.append("after")


def _local_definition(name: str = "math.add") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Add numbers",
        executor_type="local",
        input_schema={"type": "object"},
    )


def test_pipeline_executes_local_tool_via_engine() -> None:
    handlers = LocalHandlerRegistry()
    handlers.register("math.add", lambda a, b: a + b)
    engine = create_default_tool_execution_engine(handlers)
    pipeline = ExecutionPipeline(tool_execution_engine=engine)
    context = attach_tool_request(
        RuntimeContext(execution_id="exec-tool-1", agent_id="agent-1"),
        _local_definition(),
        {"a": 3, "b": 4},
    )

    output = pipeline.run(context, "ignored task")

    assert output == 7


def test_pipeline_executes_remote_tool_via_engine() -> None:
    def handler(request: ToolProviderRequest) -> ToolProviderResponse:
        return ToolProviderResponse(
            success=True,
            output={"tool": request.tool_name, "args": request.arguments},
        )

    engine = create_tool_execution_engine(
        remote_client=InMemoryRemoteClient(handler=handler),
    )
    pipeline = ExecutionPipeline(tool_execution_engine=engine)
    definition = ToolDefinition(
        name="remote.capability",
        description="Remote stub",
        executor_type="remote",
        input_schema={"type": "object"},
    )
    context = attach_tool_request(
        RuntimeContext(execution_id="exec-tool-2", agent_id="agent-1"),
        definition,
        {"query": "value"},
    )

    output = pipeline.run(context, "remote task")

    assert output == {"tool": "remote.capability", "args": {"query": "value"}}


def test_pipeline_without_tool_keeps_default_step_output() -> None:
    pipeline = ExecutionPipeline()

    output = pipeline.run(
        RuntimeContext(execution_id="exec-default", agent_id="agent-1"),
        "plain task",
    )

    assert output == "pipeline execution completed"


def test_pipeline_tool_request_requires_engine() -> None:
    pipeline = ExecutionPipeline(tool_execution_engine=None)
    context = attach_tool_request(
        RuntimeContext(execution_id="exec-tool-3", agent_id="agent-1"),
        _local_definition(),
        {"a": 1, "b": 2},
    )

    with pytest.raises(ToolExecutionEngineRequiredError):
        pipeline.run(context, "tool task")


def test_pipeline_preserves_hook_lifecycle_order() -> None:
    handlers = LocalHandlerRegistry()
    handlers.register("math.add", lambda a, b: a + b)
    engine = create_default_tool_execution_engine(handlers)
    hook = RecordingHook()
    pipeline = ExecutionPipeline(hooks=[hook], tool_execution_engine=engine)
    context = attach_tool_request(
        RuntimeContext(execution_id="exec-tool-4", agent_id="agent-1"),
        _local_definition(),
        {"a": 1, "b": 1},
    )

    pipeline.run(context, "tool task")

    assert hook.events == ["before", "after"]


def test_agent_executor_routes_tool_context_through_pipeline() -> None:
    handlers = LocalHandlerRegistry()
    handlers.register("math.add", lambda a, b: a + b)
    engine = create_default_tool_execution_engine(handlers)
    pipeline = ExecutionPipeline(tool_execution_engine=engine)
    executor = AgentExecutor(pipeline=pipeline)
    context = attach_tool_request(
        RuntimeContext(execution_id="exec-tool-5", agent_id="agent-1"),
        _local_definition(),
        {"a": 10, "b": 5},
    )

    result = executor.execute(agent_id="agent-1", task="tool task", context=context)

    assert result.status == "SUCCESS"
    assert result.output == 15


def test_pipeline_does_not_bypass_tool_execution_engine() -> None:
    from app.runtime.pipeline import tool_step as tool_step_module

    with open(ExecutionPipeline._execute_step.__code__.co_filename, encoding="utf-8") as handle:
        pipeline_source = handle.read().lower()
    with open(tool_step_module.__file__, encoding="utf-8") as handle:
        tool_step_source = handle.read().lower()

    for source in (pipeline_source, tool_step_source):
        assert "localhandlerregistry" not in source
        assert "remotetoolclient" not in source
        assert "tool.execute" not in source
    assert "tool_execution_engine.execute" in tool_step_source


def test_memory_and_trace_hooks_still_run_for_tool_execution() -> None:
    handlers = LocalHandlerRegistry()
    handlers.register("math.add", lambda a, b: a + b)
    engine = create_default_tool_execution_engine(handlers)
    provider = InMemoryProvider()
    pipeline = ExecutionPipeline(
        hooks=[TraceHook(), MemoryHook(provider)],
        tool_execution_engine=engine,
    )
    context = attach_tool_request(
        RuntimeContext(
            execution_id="exec-tool-6",
            agent_id="agent-1",
            metadata={"memory_key": "session-tool"},
        ),
        _local_definition(),
        {"a": 2, "b": 3},
    )

    output = pipeline.run(context, "tool task")

    assert output == 5
    assert provider.get("session-tool") == 5
    trace = context.metadata.get(RUNTIME_TRACE_KEY)
    assert isinstance(trace, dict)
    events = trace.get("events")
    assert isinstance(events, list)
    assert len(events) >= 2
    assert get_tool_definition(context) is not None
