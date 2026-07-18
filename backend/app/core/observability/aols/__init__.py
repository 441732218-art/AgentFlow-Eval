# (c) 2026 AgentFlow-Eval
"""AgentFlow Observability Logging System (AOLS) — structured event logging."""

from app.core.observability.aols.context import (
    bind_request_context,
    clear_request_context,
    get_bound_context,
    new_error_id,
)
from app.core.observability.aols.emit import (
    detect_and_emit_loop,
    emit_agent,
    emit_agent_step,
    emit_evaluation,
    emit_llm,
    emit_tool,
    map_step_type,
    new_execution_id,
)
from app.core.observability.aols.events import LogEvent
from app.core.observability.aols.logger import get_logger, setup_aols_logging
from app.core.observability.aols.redaction import redact_mapping, redact_value

__all__ = [
    "LogEvent",
    "bind_request_context",
    "clear_request_context",
    "detect_and_emit_loop",
    "emit_agent",
    "emit_agent_step",
    "emit_evaluation",
    "emit_llm",
    "emit_tool",
    "get_bound_context",
    "get_logger",
    "map_step_type",
    "new_error_id",
    "new_execution_id",
    "redact_mapping",
    "redact_value",
    "setup_aols_logging",
]
