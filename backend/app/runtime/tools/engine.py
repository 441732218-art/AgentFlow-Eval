# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool execution engine — routes ``ToolDefinition`` to executor adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.executor_registry import (
    ToolExecutorRegistry,
    UnknownExecutorTypeError,
)


@dataclass
class ToolExecutionResult:
    """Outcome of a single tool execution routed through an adapter."""

    tool_name: str
    executor_type: str
    output: Any


class ToolExecutionEngine:
    """Resolve ``executor_type`` and delegate execution to a registered adapter."""

    def __init__(self, adapter_registry: ToolExecutorRegistry | None = None) -> None:
        self.adapter_registry = adapter_registry or ToolExecutorRegistry()

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """Execute a tool definition via the matching executor adapter.

        Raises:
            TypeError: If ``tool_definition`` is not a ``ToolDefinition``.
            UnknownExecutorTypeError: If no adapter is registered for the type.
        """
        if not isinstance(tool_definition, ToolDefinition):
            raise TypeError(
                f"Expected ToolDefinition, got {type(tool_definition).__name__}"
            )

        executor_type = tool_definition.executor_type
        adapter = self.adapter_registry.get(executor_type)
        if adapter is None:
            raise UnknownExecutorTypeError(executor_type)

        output = adapter.execute(tool_definition, dict(arguments or {}))
        return ToolExecutionResult(
            tool_name=tool_definition.name,
            executor_type=executor_type,
            output=output,
        )
