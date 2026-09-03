# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool invocation errors."""

from __future__ import annotations


class ToolInvocationDeniedError(Exception):
    """Raised when tool invocation governance denies execution."""

    def __init__(self, tool_name: str, reason: str | None = None) -> None:
        self.tool_name = tool_name
        self.reason = reason or f"Tool invocation denied: {tool_name}"
        super().__init__(self.reason)
