# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool Registry — bridge between Runtime and external business systems."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from app.runtime.tools.definition import (
    ALLOWED_EXECUTOR_TYPES,
    ToolDefinition,
    validate_tool_definition,
)


class ToolMetadata(TypedDict):
    """Public metadata returned by ``ToolRegistry.list_tools``."""

    name: str
    description: str
    executor_type: str


class DuplicateToolError(Exception):
    """Raised when ``register`` is called with an existing tool name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Tool already registered: {name}")


class Tool(ABC):
    """Legacy executable tool contract (deprecated — use ``ToolDefinition``)."""

    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Run the tool with keyword arguments supplied by the executor."""


def tool_definition_from_legacy(tool: Tool) -> ToolDefinition:
    """Convert a legacy ``Tool`` instance to ``ToolDefinition`` (executor_type=local)."""
    return ToolDefinition(
        name=(tool.name or "").strip(),
        description=(tool.description or "").strip(),
        executor_type="local",
        input_schema={},
        metadata={"legacy_tool": True},
    )


class ToolRegistry:
    """Register and resolve tool capability definitions by name."""

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition | Tool) -> None:
        """Register a tool capability definition.

        Legacy ``Tool`` instances are accepted temporarily and coerced to
        ``ToolDefinition`` with ``executor_type='local'``.

        Raises:
            TypeError: If ``tool`` is not ``ToolDefinition`` or legacy ``Tool``.
            ValueError: If the definition is invalid.
            DuplicateToolError: If a tool with the same name is already registered.
        """
        definition = self._coerce_definition(tool)
        validate_tool_definition(definition)
        if definition.name in self._definitions:
            raise DuplicateToolError(definition.name)
        stored = ToolDefinition(
            name=definition.name,
            description=definition.description,
            executor_type=definition.executor_type,
            input_schema=dict(definition.input_schema),
            metadata=dict(definition.metadata),
        )
        self._definitions[definition.name] = stored

    def get(self, name: str) -> ToolDefinition | None:
        """Return a tool definition by name, or ``None`` if not registered."""
        return self._definitions.get(name)

    def list_tools(self) -> list[ToolMetadata]:
        """Return public metadata for all registered tools (insertion order)."""
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "executor_type": definition.executor_type,
            }
            for definition in self._definitions.values()
        ]

    def _coerce_definition(self, tool: ToolDefinition | Tool) -> ToolDefinition:
        if isinstance(tool, ToolDefinition):
            return ToolDefinition(
                name=(tool.name or "").strip(),
                description=(tool.description or "").strip(),
                executor_type=(tool.executor_type or "").strip(),
                input_schema=tool.input_schema,
                metadata=tool.metadata,
            )
        if isinstance(tool, Tool):
            warnings.warn(
                "Tool ABC is deprecated; register ToolDefinition instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            return tool_definition_from_legacy(tool)
        raise TypeError(
            "Expected ToolDefinition or legacy Tool instance, "
            f"got {type(tool).__name__}"
        )


__all__ = [
    "ALLOWED_EXECUTOR_TYPES",
    "DuplicateToolError",
    "Tool",
    "ToolDefinition",
    "ToolMetadata",
    "ToolRegistry",
    "tool_definition_from_legacy",
    "validate_tool_definition",
]
