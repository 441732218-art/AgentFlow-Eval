# AgentFlow Intelligence v2.0 — Tool Registry unit tests (Phase 8.1)

from __future__ import annotations

from typing import Any

import pytest

from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.registry import (
    DuplicateToolError,
    Tool,
    ToolNotFoundError,
    ToolRegistry,
    tool_definition_from_legacy,
)


def _remote_definition(name: str = "crm.search_customer") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Search customer records",
        executor_type="remote",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        metadata={"provider": "crm", "version": "1"},
    )


class EchoTool(Tool):
    """Legacy test tool."""

    name = "test.echo"
    description = "Echo input for unit tests"

    def execute(self, **kwargs: Any) -> Any:
        return kwargs.get("message", "")


def test_register_tool_definition_success() -> None:
    registry = ToolRegistry()
    definition = _remote_definition()

    registry.register(definition)

    stored = registry.get("crm.search_customer")
    assert stored == definition
    assert stored is not None
    assert stored.executor_type == "remote"
    assert stored.input_schema["type"] == "object"


def test_get_returns_tool_definition() -> None:
    registry = ToolRegistry()
    definition = _remote_definition(name="test.get")
    registry.register(definition)

    fetched = registry.get("test.get")
    assert isinstance(fetched, ToolDefinition)
    assert fetched.name == "test.get"
    assert fetched.metadata["provider"] == "crm"


def test_list_tools_returns_public_metadata_only() -> None:
    registry = ToolRegistry()
    registry.register(_remote_definition())
    registry.register(
        ToolDefinition(
            name="email.send",
            description="Send email",
            executor_type="future_provider",
            input_schema={"type": "object"},
            metadata={"secret": "internal"},
        )
    )

    tools = registry.list_tools()

    assert tools == [
        {
            "name": "crm.search_customer",
            "description": "Search customer records",
            "executor_type": "remote",
        },
        {
            "name": "email.send",
            "description": "Send email",
            "executor_type": "future_provider",
        },
    ]
    for item in tools:
        assert "input_schema" not in item
        assert "metadata" not in item
        assert "execute" not in item


def test_duplicate_register_raises() -> None:
    registry = ToolRegistry()
    registry.register(_remote_definition())
    with pytest.raises(DuplicateToolError) as exc:
        registry.register(_remote_definition())
    assert exc.value.name == "crm.search_customer"


def test_register_rejects_invalid_executor_type() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        name="bad.executor",
        description="invalid",
        executor_type="unknown",
        input_schema={},
    )
    with pytest.raises(ValueError, match="executor_type"):
        registry.register(definition)


def test_register_rejects_empty_name() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        name="   ",
        description="invalid",
        executor_type="local",
        input_schema={},
    )
    with pytest.raises(ValueError, match="ToolDefinition.name"):
        registry.register(definition)


def test_register_rejects_non_dict_input_schema() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        name="bad.schema",
        description="invalid schema",
        executor_type="local",
        input_schema=[],  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="input_schema"):
        registry.register(definition)


def test_get_missing_raises_tool_not_found() -> None:
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError) as exc:
        registry.get("missing.tool")
    assert exc.value.name == "missing.tool"


def test_register_rejects_unsupported_type() -> None:
    registry = ToolRegistry()
    with pytest.raises(TypeError, match="ToolDefinition or legacy Tool"):
        registry.register(object())  # type: ignore[arg-type]


def test_legacy_tool_temporarily_compatible() -> None:
    registry = ToolRegistry()
    with pytest.warns(DeprecationWarning, match="Tool ABC is deprecated"):
        registry.register(EchoTool())

    definition = registry.get("test.echo")
    assert isinstance(definition, ToolDefinition)
    assert definition.executor_type == "local"
    assert definition.metadata.get("legacy_tool") is True

    assert EchoTool().execute(message="hello") == "hello"


def test_tool_definition_from_legacy_helper() -> None:
    definition = tool_definition_from_legacy(EchoTool())
    assert definition.name == "test.echo"
    assert definition.executor_type == "local"
    assert definition.metadata["legacy_tool"] is True
