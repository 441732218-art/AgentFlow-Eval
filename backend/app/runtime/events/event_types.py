# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance event type identifiers."""

from __future__ import annotations

from enum import Enum


class RuntimeEventType(str, Enum):
    """Enterprise runtime event types for governance and audit."""

    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    TOOL_POLICY_DENIED = "tool.policy.denied"
