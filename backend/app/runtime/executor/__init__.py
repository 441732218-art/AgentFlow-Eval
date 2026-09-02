# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent execution pipeline."""

from __future__ import annotations

from app.runtime.executor.context_fields import (
    TOOL_ARGUMENTS_METADATA_KEY,
    TOOL_DEFINITION_METADATA_KEY,
    attach_execution_context,
    attach_tool_request,
    ensure_execution_context,
    get_execution_context,
    get_tool_arguments,
    get_tool_definition,
)
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.executor.executor import AgentExecutor, ExecutionResult

__all__ = [
    "AgentExecutor",
    "ExecutionContext",
    "ExecutionResult",
    "TOOL_ARGUMENTS_METADATA_KEY",
    "TOOL_DEFINITION_METADATA_KEY",
    "attach_execution_context",
    "attach_tool_request",
    "ensure_execution_context",
    "get_execution_context",
    "get_tool_arguments",
    "get_tool_definition",
]
