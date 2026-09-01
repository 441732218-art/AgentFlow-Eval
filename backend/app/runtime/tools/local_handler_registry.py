# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Registry of local Python callables keyed by tool name."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.runtime.tools.registry import Tool


class DuplicateLocalHandlerError(Exception):
    """Raised when a handler is registered for an existing tool name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Local handler already registered: {name}")


class MissingLocalHandlerError(Exception):
    """Raised when no local handler exists for a tool name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"No local handler registered for: {name}")


LocalHandler = Callable[..., Any]


class LocalHandlerRegistry:
    """Register and resolve local Python callables by tool name."""

    def __init__(self) -> None:
        self._handlers: dict[str, LocalHandler] = {}

    def register(self, name: str, handler: LocalHandler) -> None:
        """Register a callable for ``name``.

        Raises:
            ValueError: If ``name`` is empty.
            TypeError: If ``handler`` is not callable.
            DuplicateLocalHandlerError: If ``name`` is already registered.
        """
        tool_name = (name or "").strip()
        if not tool_name:
            raise ValueError("Local handler name must be a non-empty string")
        if not callable(handler):
            raise TypeError(f"Expected callable handler, got {type(handler).__name__}")
        if tool_name in self._handlers:
            raise DuplicateLocalHandlerError(tool_name)
        self._handlers[tool_name] = handler

    def get(self, name: str) -> LocalHandler | None:
        """Return a handler for ``name``, or ``None`` if not registered."""
        return self._handlers.get(name)


def register_legacy_tool_handler(
    handler_registry: LocalHandlerRegistry,
    tool: Tool,
) -> None:
    """Register a legacy ``Tool`` instance's ``execute`` method as its local handler."""
    if not isinstance(tool, Tool):
        raise TypeError(f"Expected Tool instance, got {type(tool).__name__}")
    tool_name = (tool.name or "").strip()
    if not tool_name:
        raise ValueError("Tool.name must be a non-empty string")
    handler_registry.register(tool_name, tool.execute)
