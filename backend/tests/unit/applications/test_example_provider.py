# AgentFlow Intelligence v2.0 — Application layer unit tests (Phase 8.7)

from __future__ import annotations

from pathlib import Path

import pytest

from app.applications.bootstrap import bootstrap_applications
from app.applications.example_provider.tools import TOOL_DEFINITIONS
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.registry import ToolNotFoundError, create_tool_registry
from app.runtime.tools.remote_client import InMemoryRemoteClient

_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_RUNTIME_CORE_EXCLUDED_PARTS = frozenset({"service"})
_FORBIDDEN_RUNTIME_STRINGS = (
    "example_provider",
    "app.applications",
    "app_example.echo",
    "app_example.remote_search",
)


def test_runtime_core_has_no_application_leakage() -> None:
    for path in _RUNTIME_ROOT.rglob("*.py"):
        relative_parts = path.relative_to(_RUNTIME_ROOT).parts
        if relative_parts and relative_parts[0] in _RUNTIME_CORE_EXCLUDED_PARTS:
            continue
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_RUNTIME_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"


def test_bootstrap_applications_registers_app_example_tools() -> None:
    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)

    echo = registry.get("app_example.echo")
    remote = registry.get("app_example.remote_search")

    assert echo.executor_type == "local"
    assert remote.executor_type == "remote"
    assert handlers.get("app_example.echo") is not None


def test_local_application_tool_end_to_end() -> None:
    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)
    engine = create_tool_execution_engine(handler_registry=handlers)

    definition = registry.get("app_example.echo")
    result = engine.execute(definition, {"message": "from-application"})

    assert result.tool_name == "app_example.echo"
    assert result.executor_type == "local"
    assert result.output == {"app_echo": "from-application"}


def test_remote_application_tool_end_to_end() -> None:
    captured: list[ToolProviderRequest] = []

    def handler(request: ToolProviderRequest) -> ToolProviderResponse:
        captured.append(request)
        return ToolProviderResponse(
            success=True,
            output={"app_results": [request.arguments.get("query", "")]},
        )

    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)
    client = InMemoryRemoteClient(handler=handler)
    engine = create_tool_execution_engine(
        handler_registry=handlers,
        remote_client=client,
    )

    definition = registry.get("app_example.remote_search")
    result = engine.execute(definition, {"query": "app-layer"})

    assert result.tool_name == "app_example.remote_search"
    assert result.output == {"app_results": ["app-layer"]}
    assert len(captured) == 1


def test_runtime_self_check_registry_does_not_include_application_tools() -> None:
    """Runtime unit-test bootstrap without application layer remains isolated."""
    registry = create_tool_registry(bootstrap=True)

    assert registry.get("example.echo").name == "example.echo"
    with pytest.raises(ToolNotFoundError):
        registry.get("app_example.echo")


def test_application_and_runtime_examples_coexist_without_conflict() -> None:
    registry = create_tool_registry(bootstrap=True)
    handlers = LocalHandlerRegistry()
    from app.runtime.tools.bootstrap import bootstrap_local_handlers

    bootstrap_local_handlers(handlers)
    bootstrap_applications(registry, handlers)

    assert registry.get("example.echo").name == "example.echo"
    assert registry.get("app_example.echo").name == "app_example.echo"
    assert registry.get("trade.generate_email").name == "trade.generate_email"
    assert len(registry.list_tools()) == len(TOOL_DEFINITIONS) + 2 + 3


def test_tool_definition_names_use_app_example_prefix() -> None:
    names = {definition.name for definition in TOOL_DEFINITIONS}
    assert names == {"app_example.echo", "app_example.remote_search"}
    for name in names:
        assert name.startswith("app_example.")
