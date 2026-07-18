# (c) 2026 AgentFlow-Eval
"""Canonical observability log events (dot-notation wire format)."""

from __future__ import annotations

from enum import Enum


class LogEvent(str, Enum):
    """Structured log event names.

    Wire format uses the enum *value* (e.g. ``http.request``).
    """

    # HTTP
    HTTP_REQUEST = "http.request"
    HTTP_REQUEST_FAILED = "http.request.failed"

    # Evaluation lifecycle (Phase 3 will emit heavily)
    EVALUATION_CREATED = "evaluation.created"
    EVALUATION_STARTED = "evaluation.started"
    EVALUATION_RUNNING = "evaluation.running"
    EVALUATION_COMPLETED = "evaluation.completed"
    EVALUATION_FAILED = "evaluation.failed"

    # Agent
    AGENT_STARTED = "agent.started"
    AGENT_STEP_COMPLETED = "agent.step.completed"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_LOOP_DETECTED = "agent.loop.detected"

    # LLM
    LLM_STARTED = "llm.started"
    LLM_COMPLETED = "llm.completed"
    LLM_FAILED = "llm.failed"

    # Tool
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    TOOL_TIMEOUT = "tool.timeout"

    # Analytics / diagnosis signals
    TOKEN_ANOMALY_DETECTED = "token.anomaly.detected"
    PROMPT_PERFORMANCE_DEGRADED = "prompt.performance.degraded"

    # System
    SYSTEM_ERROR = "system.error"
    SYSTEM_INFO = "system.info"
    DB_ERROR = "db.error"
    AUDIT = "audit.event"

    def __str__(self) -> str:
        return self.value
