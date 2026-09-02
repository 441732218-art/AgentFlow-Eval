# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Local executor adapter — runs Python callables via ``LocalHandlerRegistry``."""

from __future__ import annotations

from typing import Any

from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.local_handler_registry import (
    LocalHandlerRegistry,
    MissingLocalHandlerError,
)


class LocalToolExecutorAdapter(ToolExecutorAdapter):
    """Execute ``executor_type='local'`` tools through registered callables."""

    executor_type = "local"

    def __init__(self, handler_registry: LocalHandlerRegistry | None = None) -> None:
        self.handler_registry = handler_registry or LocalHandlerRegistry()

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: Any | None = None,
    ) -> Any:
        """Resolve handler by ``tool_definition.name`` and invoke ``handler(**arguments)``."""
        _ = execution_context
        handler = self.handler_registry.get(tool_definition.name)
        if handler is None:
            raise MissingLocalHandlerError(tool_definition.name)
        return handler(**arguments)
