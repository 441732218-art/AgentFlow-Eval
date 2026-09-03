# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Pipeline tool step — routes tool requests through ``ToolExecutionEngine`` only."""

from __future__ import annotations

import time
from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import (
    ensure_execution_context,
    get_execution_context,
    get_tool_arguments,
    get_tool_definition,
)
from app.runtime.governance.middleware import use_governance_lifecycle
from app.runtime.correlation.context import get_correlation_context
from app.runtime.observability.events import RuntimeEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.invocation_event import ToolInvocationEvent


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

    ensure_execution_context(context)
    execution_context = get_execution_context(context)

    if use_governance_lifecycle(execution_context):
        result = tool_execution_engine.execute(
            tool_definition,
            get_tool_arguments(context),
            context=execution_context,
        )
        return result.output

    tool_name = tool_definition.name
    correlation = get_correlation_context(context)
    start_time = time.monotonic()
    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            RuntimeEventType.TOOL_STARTED,
            tool_name=tool_name,
            metadata={"executor_type": tool_definition.executor_type},
            correlation=correlation,
        ),
    )

    try:
        result = tool_execution_engine.execute(
            tool_definition,
            get_tool_arguments(context),
            context=execution_context,
        )
    except Exception as exc:
        end_time = time.monotonic()
        invocation = ToolInvocationEvent(
            execution_id=execution_context.execution_id if execution_context else "",
            tool_name=tool_name,
            started_at=start_time,
            finished_at=end_time,
            status="failed",
            error_type=type(exc).__name__,
        )
        record_runtime_event(
            execution_context,
            build_runtime_event(
                execution_context,
                RuntimeEventType.TOOL_FAILED,
                tool_name=tool_name,
                status="failed",
                duration_ms=invocation.duration_ms,
                metadata={
                    "executor_type": tool_definition.executor_type,
                    "error_type": invocation.error_type,
                },
                correlation=correlation,
            ),
        )
        raise

    end_time = time.monotonic()
    invocation = ToolInvocationEvent(
        execution_id=execution_context.execution_id if execution_context else "",
        tool_name=tool_name,
        started_at=start_time,
        finished_at=end_time,
        status="success",
    )
    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            RuntimeEventType.TOOL_COMPLETED,
            tool_name=tool_name,
            status="success",
            duration_ms=invocation.duration_ms,
            metadata={"executor_type": tool_definition.executor_type},
            correlation=correlation,
        ),
    )
    return result.output
