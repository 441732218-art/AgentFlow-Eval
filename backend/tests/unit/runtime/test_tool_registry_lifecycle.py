# AgentFlow Intelligence v2.0 — Tool Registry lifecycle tests (Phase 8.5)

from __future__ import annotations

import pytest

from app.runtime.tools.bootstrap import (
    DEFAULT_TOOL_DEFINITIONS,
    EXAMPLE_REMOTE_ENDPOINT,
    example_echo_handler,
)
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.registry import (
    DuplicateToolError,
    ToolNotFoundError,
    create_tool_registry,
    get_local_handler_registry,
    get_tool_registry,
    reset_tool_registry,
)
from app.runtime.tools.remote_client import InMemoryRemoteClient


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    reset_tool_registry()
    yield
    reset_tool_registry()


def test_singleton_registry_bootstraps_example_definitions() -> None:
    registry = get_tool_registry()
    names = {item["name"] for item in registry.list_tools()}

    assert names == {"example.echo", "example.remote_search"}
    assert len(DEFAULT_TOOL_DEFINITIONS) == 2


def test_get_returns_registered_tool_definition() -> None:
    registry = get_tool_registry()

    definition = registry.get("example.echo")

    assert isinstance(definition, ToolDefinition)
    assert definition.executor_type == "local"
    assert definition.metadata.get("example") is True


def test_get_missing_raises_tool_not_found() -> None:
    registry = get_tool_registry()

    with pytest.raises(ToolNotFoundError) as exc:
        registry.get("example.missing")

    assert exc.value.name == "example.missing"


def test_duplicate_register_raises_duplicate_tool_error() -> None:
    registry = create_tool_registry(bootstrap=True)
    duplicate = ToolDefinition(
        name="example.echo",
        description="duplicate registration attempt",
        executor_type="local",
        input_schema={"type": "object"},
    )

    with pytest.raises(DuplicateToolError) as exc:
        registry.register(duplicate)

    assert exc.value.name == "example.echo"


def test_local_tool_end_to_end_via_registry_and_engine() -> None:
    registry = get_tool_registry()
    handlers = get_local_handler_registry()
    engine = create_tool_execution_engine(handler_registry=handlers)

    definition = registry.get("example.echo")
    result = engine.execute(definition, {"message": "phase-8.5"})

    assert result.tool_name == "example.echo"
    assert result.executor_type == "local"
    assert result.output == {"echo": "phase-8.5"}
    assert example_echo_handler(message="direct") == {"echo": "direct"}


def test_remote_tool_end_to_end_via_registry_engine_and_mock_provider() -> None:
    captured: list[ToolProviderRequest] = []

    def mock_provider_handler(request: ToolProviderRequest) -> ToolProviderResponse:
        captured.append(request)
        return ToolProviderResponse(
            success=True,
            output={"results": [request.arguments.get("query", "")]},
            metadata={"transport": "in_memory_mock"},
        )

    registry = get_tool_registry()
    client = InMemoryRemoteClient(handler=mock_provider_handler)
    engine = create_tool_execution_engine(remote_client=client)

    definition = registry.get("example.remote_search")
    assert definition.metadata.get("endpoint") == EXAMPLE_REMOTE_ENDPOINT
    assert definition.executor_type == "remote"

    result = engine.execute(definition, {"query": "mock-search-term"})

    assert result.tool_name == "example.remote_search"
    assert result.executor_type == "remote"
    assert result.output == {"results": ["mock-search-term"]}
    assert len(captured) == 1
    assert captured[0].tool_name == "example.remote_search"
    assert captured[0].arguments == {"query": "mock-search-term"}
    assert captured[0].metadata["provider_id"] == "example-mock-provider"


def test_get_tool_registry_returns_same_instance() -> None:
    first = get_tool_registry()
    second = get_tool_registry()

    assert first is second


def test_get_local_handler_registry_returns_same_instance() -> None:
    first = get_local_handler_registry()
    second = get_local_handler_registry()

    assert first is second


def test_reset_tool_registry_creates_fresh_singleton() -> None:
    first = get_tool_registry()
    reset_tool_registry()
    second = get_tool_registry()

    assert first is not second
    assert second.get("example.echo").name == "example.echo"
