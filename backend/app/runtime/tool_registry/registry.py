# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool capability registry interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.runtime.tool_registry.errors import ToolDisabledError, ToolNotFoundError
from app.runtime.tool_registry.models import ToolCapability


@runtime_checkable
class ToolRegistry(Protocol):
    """Runtime tool capability registry for discovery and validation."""

    def register(self, tool: ToolCapability) -> None:
        """Register or replace a tool capability."""

    def get(self, tool_name: str) -> ToolCapability | None:
        """Return a tool capability by name."""

    def list_tools(self) -> list[ToolCapability]:
        """Return all registered tool capabilities."""

    def remove(self, tool_name: str) -> None:
        """Remove a tool capability by name."""


def resolve_tool_capability(registry: ToolRegistry, tool_name: str) -> ToolCapability:
    """Validate that a tool exists and is enabled."""
    capability = registry.get(tool_name)
    if capability is None:
        raise ToolNotFoundError(tool_name)
    if not capability.enabled:
        raise ToolDisabledError(tool_name)
    return capability
