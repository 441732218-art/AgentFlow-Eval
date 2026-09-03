# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool capability registry errors."""

from __future__ import annotations


class ToolNotFoundError(LookupError):
    """Raised when a required tool capability is not registered."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool capability not found: {tool_name}")


class ToolDisabledError(RuntimeError):
    """Raised when a registered tool capability is disabled."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool capability is disabled: {tool_name}")
