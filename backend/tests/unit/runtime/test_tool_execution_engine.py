# AgentFlow Intelligence v2.0 — Tool Execution Engine unit tests (Phase 8.2.1)

from __future__ import annotations

from typing import Any

import pytest

from app.runtime.executor.context_fields import (
    TENANT_ID_METADATA_KEY,
    USER_ID_METADATA_KEY,
    attach_execution_context,
)
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine, ToolExecutionResult
from app.runtime.tools.executor_registry import (
    DuplicateExecutorAdapterError,
    ToolExecutorRegistry,
    UnknownExecutorTypeError,
)
from app.runtime.tools.registry import Tool, tool_definition_from_legacy


class StubAdapter(ToolExecutorAdapter):
    """Test adapter that records invocations without business logic."""

    executor_type = "local"

    def __init__(self) -> None:
        self.calls: list[
            tuple[ToolDefinition, dict[str, Any], ExecutionContext | None]
        ] = []

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        self.calls.append((tool_definition, arguments, execution_context))
        return {"tool": tool_definition.name, "args": arguments}


class RemoteStubAdapter(ToolExecutorAdapter):
    """Placeholder remote adapter (no HTTP — skeleton only)."""

    executor_type = "remote"

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = execution_context
        return {"status": "remote_stub", "tool": tool_definition.name}


class EchoTool(Tool):
    name = "legacy.echo"
    description = "Legacy echo tool"

    def execute(self, **kwargs: Any) -> Any:
        return kwargs.get("message", "")


def _definition(
    name: str = "test.tool",
    executor_type: str = "local",
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Test tool",
        executor_type=executor_type,
        input_schema={"type": "object"},
        metadata={"test": True},
    )


def test_register_adapter_success() -> None:
    registry = ToolExecutorRegistry()
    adapter = StubAdapter()

    registry.register(adapter)

    assert registry.get("local") is adapter


def test_resolve_adapter_by_executor_type() -> None:
    registry = ToolExecutorRegistry()
    local = StubAdapter()
    remote = RemoteStubAdapter()
    registry.register(local)
    registry.register(remote)

    assert registry.get("local") is local
    assert registry.get("remote") is remote
    assert registry.get("future_provider") is None


def test_duplicate_adapter_registration_rejected() -> None:
    registry = ToolExecutorRegistry()
    registry.register(StubAdapter())
    with pytest.raises(DuplicateExecutorAdapterError) as exc:
        registry.register(StubAdapter())
    assert exc.value.executor_type == "local"


def test_unknown_executor_type_rejected_by_engine() -> None:
    engine = ToolExecutionEngine()
    definition = _definition(executor_type="remote")

    with pytest.raises(UnknownExecutorTypeError) as exc:
        engine.execute(definition, {"query": "x"})

    assert exc.value.executor_type == "remote"


def test_engine_executes_through_adapter() -> None:
    registry = ToolExecutorRegistry()
    adapter = StubAdapter()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = _definition()

    result = engine.execute(definition, {"query": "hello"})

    assert isinstance(result, ToolExecutionResult)
    assert result.tool_name == "test.tool"
    assert result.executor_type == "local"
    assert result.output == {"tool": "test.tool", "args": {"query": "hello"}}
    assert len(adapter.calls) == 1
    called_definition, called_args, _ = adapter.calls[0]
    assert called_definition.name == "test.tool"
    assert called_args == {"query": "hello"}


def test_engine_forwards_execution_context_to_adapter() -> None:
    registry = ToolExecutorRegistry()
    adapter = StubAdapter()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = _definition()
    execution_context = ExecutionContext(
        execution_id="exec-ctx-1",
        agent_id="agent-1",
        tenant_id="tenant-a",
        user_id="user-1",
    )

    engine.execute(definition, {"query": "hello"}, context=execution_context)

    assert len(adapter.calls) == 1
    _, _, forwarded = adapter.calls[0]
    assert forwarded == execution_context


def test_engine_contains_no_business_logic() -> None:
    source_path = ToolExecutionEngine.execute.__code__.co_filename
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read()
    for forbidden in ("crm", "http", "email", "sales", "redis"):
        assert forbidden not in source.lower()


def test_legacy_tool_migration_routes_via_local_adapter() -> None:
    legacy_definition = tool_definition_from_legacy(EchoTool())
    assert legacy_definition.executor_type == "local"

    registry = ToolExecutorRegistry()
    adapter = StubAdapter()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)

    result = engine.execute(legacy_definition, {"message": "hi"})

    assert result.executor_type == "local"
    assert result.output["args"] == {"message": "hi"}
    assert legacy_definition.metadata.get("legacy_tool") is True
    assert EchoTool().execute(message="hi") == "hi"
