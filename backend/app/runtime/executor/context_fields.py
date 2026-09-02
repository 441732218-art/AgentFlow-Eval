# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Minimal RuntimeContext extensions for tool execution (metadata keys)."""

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.executor.execution_context import (
    EXECUTION_CONTEXT_METADATA_KEY,
    ExecutionContext,
)
from app.runtime.tools.definition import ToolDefinition

TOOL_DEFINITION_METADATA_KEY = "tool_definition"
TOOL_ARGUMENTS_METADATA_KEY = "tool_arguments"
TENANT_ID_METADATA_KEY = "tenant_id"
USER_ID_METADATA_KEY = "user_id"


def attach_tool_request(
    context: RuntimeContext,
    tool_definition: ToolDefinition,
    tool_arguments: dict[str, Any] | None = None,
) -> RuntimeContext:
    """Attach tool execution request fields to ``context.metadata``."""
    context.metadata[TOOL_DEFINITION_METADATA_KEY] = tool_definition
    context.metadata[TOOL_ARGUMENTS_METADATA_KEY] = dict(tool_arguments or {})
    return context


def attach_execution_context(
    context: RuntimeContext,
    execution_context: ExecutionContext,
) -> RuntimeContext:
    """Attach an ``ExecutionContext`` to ``context.metadata``."""
    context.metadata[EXECUTION_CONTEXT_METADATA_KEY] = execution_context
    return context


def get_execution_context(context: RuntimeContext) -> ExecutionContext | None:
    """Return an ``ExecutionContext`` from runtime metadata, if present."""
    value = context.metadata.get(EXECUTION_CONTEXT_METADATA_KEY)
    if value is None:
        return None
    if not isinstance(value, ExecutionContext):
        raise TypeError(
            "context.metadata.execution_context must be an ExecutionContext instance"
        )
    return value


def ensure_execution_context(context: RuntimeContext) -> ExecutionContext | None:
    """Resolve or materialize ``ExecutionContext`` on ``context`` when possible."""
    existing = get_execution_context(context)
    if existing is not None:
        return existing

    tenant_id = context.metadata.get(TENANT_ID_METADATA_KEY)
    user_id = context.metadata.get(USER_ID_METADATA_KEY)
    if tenant_id is None and user_id is None:
        return None

    execution_context = ExecutionContext(
        execution_id=context.execution_id,
        agent_id=context.agent_id,
        tenant_id=str(tenant_id) if tenant_id is not None else None,
        user_id=str(user_id) if user_id is not None else None,
        metadata={},
    )
    attach_execution_context(context, execution_context)
    return execution_context


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
