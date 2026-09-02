# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool invocation event model for enterprise governance (in-memory only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InvocationStatus = Literal["success", "error"]


@dataclass
class ToolInvocationEvent:
    """Minimal in-memory record of a single tool invocation."""

    execution_id: str
    tool_name: str
    started_at: float
    finished_at: float
    status: InvocationStatus
    error_type: str | None = None
