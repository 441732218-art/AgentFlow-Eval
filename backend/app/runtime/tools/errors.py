# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime tool execution errors — unified boundary for external failures."""

from __future__ import annotations


class ToolExecutionError(Exception):
    """Base error for tool execution failures within Runtime."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.cause = cause
        super().__init__(message)


class RemoteProviderError(ToolExecutionError):
    """Remote provider returned a failure or raised an execution error."""


class RemoteTimeoutError(ToolExecutionError):
    """Remote provider did not respond within the allowed time."""


class RemoteResponseValidationError(ToolExecutionError):
    """Remote provider returned a response that violates the protocol contract."""


class ToolInputValidationError(ToolExecutionError):
    """Tool arguments failed validation against input_schema."""
