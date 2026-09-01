# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Minimal RuntimeContext extensions for tool execution (metadata keys)."""

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.tools.definition import ToolDefinition

TOOL_DEFINITION_METADATA_KEY = "tool_definition"
TOOL_ARGUMENTS_METADATA_KEY = "tool_arguments"


def attach_tool_request(
    context: RuntimeContext,
    tool_definition: ToolDefinition,
    tool_arguments: dict[str, Any] | None = None,
) -> RuntimeContext:
    """Attach tool execution request fields to ``context.metadata``."""
    context.metadata[TOOL_DEFINITION_METADATA_KEY] = tool_definition
    context.metadata[TOOL_ARGUMENTS_METADATA_KEY] = dict(tool_arguments or {})
    return context


def get_tool_definition(context: RuntimeContext) -> ToolDefinition | None:
    """Return a ``ToolDefinition`` from context metadata, if present."""
    value = context.metadata.get(TOOL_DEFINITION_METADATA_KEY)
    if value is None:
        return None
    if not isinstance(value, ToolDefinition):
        raise TypeError(
            "context.metadata.tool_definition must be a ToolDefinition instance"
        )
    return value


def get_tool_arguments(context: RuntimeContext) -> dict[str, Any]:
    """Return tool arguments from context metadata."""
    value = context.metadata.get(TOOL_ARGUMENTS_METADATA_KEY, {})
    if not isinstance(value, dict):
        raise TypeError("context.metadata.tool_arguments must be a dict")
    return dict(value)
