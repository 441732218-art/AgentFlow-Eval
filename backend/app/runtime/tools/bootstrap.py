# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Explicit example tool registration source for lifecycle verification.

This module is for tests and Phase 8.5 validation only. It is not wired into
RuntimeService production defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import ToolRegistry

# Mock endpoint URL — documentation / test routing only (no real HTTP in bootstrap).
EXAMPLE_REMOTE_ENDPOINT = "http://mock.test/tools/invoke"

DEFAULT_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="example.echo",
        description="Example echo tool for lifecycle verification",
        executor_type="local",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
        metadata={"example": True},
    ),
    ToolDefinition(
        name="example.remote_search",
        description="Example remote search tool (remote provider path verification)",
        executor_type="remote",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        metadata={
            "example": True,
            "endpoint": EXAMPLE_REMOTE_ENDPOINT,
            "provider_id": "example-mock-provider",
            "version": "1",
        },
    ),
]


def example_echo_handler(*, message: str = "") -> dict[str, str]:
    """Local handler for ``example.echo``."""
    return {"echo": message}


DEFAULT_LOCAL_HANDLERS: dict[str, Callable[..., Any]] = {
    "example.echo": example_echo_handler,
}


def bootstrap_tool_definitions(registry: ToolRegistry) -> None:
    """Register ``DEFAULT_TOOL_DEFINITIONS`` into ``registry``."""
    for definition in DEFAULT_TOOL_DEFINITIONS:
        registry.register(definition)


def bootstrap_local_handlers(handler_registry: LocalHandlerRegistry) -> None:
    """Register ``DEFAULT_LOCAL_HANDLERS`` into ``handler_registry``."""
    for name, handler in DEFAULT_LOCAL_HANDLERS.items():
        handler_registry.register(name, handler)
