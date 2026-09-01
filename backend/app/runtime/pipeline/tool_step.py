# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Pipeline tool step — routes tool requests through ``ToolExecutionEngine`` only."""

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import get_tool_arguments, get_tool_definition
from app.runtime.tools.engine import ToolExecutionEngine


class ToolExecutionEngineRequiredError(RuntimeError):
    """Raised when a tool request is present but no engine is configured."""


def execute_tool_via_engine(
    context: RuntimeContext,
    tool_execution_engine: ToolExecutionEngine | None,
) -> Any:
    """Execute the tool request on ``context`` via ``ToolExecutionEngine``."""
    tool_definition = get_tool_definition(context)
    if tool_definition is None:
        return None

    if tool_execution_engine is None:
        raise ToolExecutionEngineRequiredError(
            "ToolExecutionEngine is required when context includes tool_definition"
        )

    result = tool_execution_engine.execute(
        tool_definition,
        get_tool_arguments(context),
    )
    return result.output
