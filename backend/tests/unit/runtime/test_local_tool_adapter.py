# AgentFlow Intelligence v2.0 — Local Tool Adapter unit tests (Phase 8.2.2)

from __future__ import annotations

from typing import Any

import pytest

from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionResult
from app.runtime.tools.executor_registry import UnknownExecutorTypeError
from app.runtime.tools.factory import create_default_tool_execution_engine
from app.runtime.tools.local_adapter import LocalToolExecutorAdapter
from app.runtime.tools.local_handler_registry import (
    DuplicateLocalHandlerError,
    LocalHandlerRegistry,
    MissingLocalHandlerError,
    register_legacy_tool_handler,
)
from app.runtime.tools.registry import Tool, ToolRegistry, tool_definition_from_legacy


class EchoTool(Tool):
    name = "legacy.echo"
    description = "Legacy echo tool"

    def execute(self, **kwargs: Any) -> Any:
        return kwargs.get("message", "")


def _local_definition(name: str = "math.add") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Add two numbers",
        executor_type="local",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        },
        metadata={"category": "math"},
    )


def test_local_handler_registration() -> None:
    registry = LocalHandlerRegistry()

    def add_handler(a: int, b: int) -> int:
        return a + b

    registry.register("math.add", add_handler)

    handler = registry.get("math.add")
    assert handler is not None
    assert handler(2, 3) == 5
    assert registry.get("missing.tool") is None


def test_duplicate_handler_rejected() -> None:
    registry = LocalHandlerRegistry()
    registry.register("math.add", lambda a, b: a + b)

    with pytest.raises(DuplicateLocalHandlerError) as exc:
        registry.register("math.add", lambda a, b: a * b)

    assert exc.value.name == "math.add"


def test_local_adapter_executes_callable() -> None:
    handler_registry = LocalHandlerRegistry()
    handler_registry.register("math.add", lambda a, b: a + b)
    adapter = LocalToolExecutorAdapter(handler_registry)
    definition = _local_definition()

    output = adapter.execute(definition, {"a": 4, "b": 5})

    assert output == 9


def test_missing_handler_produces_controlled_error() -> None:
    adapter = LocalToolExecutorAdapter(LocalHandlerRegistry())
    definition = _local_definition(name="missing.tool")

    with pytest.raises(MissingLocalHandlerError) as exc:
        adapter.execute(definition, {"a": 1})

    assert exc.value.name == "missing.tool"


def test_engine_executes_local_tool_definition() -> None:
    handler_registry = LocalHandlerRegistry()
    handler_registry.register("math.add", lambda a, b: a + b)
    engine = create_default_tool_execution_engine(handler_registry)

    result = engine.execute(_local_definition(), {"a": 10, "b": 7})

    assert isinstance(result, ToolExecutionResult)
    assert result.tool_name == "math.add"
    assert result.executor_type == "local"
    assert result.output == 17


def test_legacy_tool_migration_still_works() -> None:
    tool = EchoTool()
    tool_registry = ToolRegistry()
    handler_registry = LocalHandlerRegistry()

    with pytest.warns(DeprecationWarning, match="Tool ABC is deprecated"):
        tool_registry.register(tool)
    register_legacy_tool_handler(handler_registry, tool)

    definition = tool_registry.get("legacy.echo")
    assert definition is not None
    assert definition.executor_type == "local"
    assert definition.metadata.get("legacy_tool") is True

    engine = create_default_tool_execution_engine(handler_registry)
    result = engine.execute(definition, {"message": "hello"})

    assert result.output == "hello"
    assert EchoTool().execute(message="hello") == "hello"


def test_remote_executor_type_still_not_implemented() -> None:
    engine = create_default_tool_execution_engine()
    remote_definition = ToolDefinition(
        name="crm.search",
        description="Remote CRM search",
        executor_type="remote",
        input_schema={"type": "object"},
        metadata={"provider": "crm"},
    )

    with pytest.raises(UnknownExecutorTypeError) as exc:
        engine.execute(remote_definition, {"query": "acme"})

    assert exc.value.executor_type == "remote"


def test_tool_definition_does_not_store_callable() -> None:
    definition = _local_definition()
    assert not hasattr(definition, "execute")
    assert not hasattr(definition, "callable")
    assert not hasattr(definition, "handler")
