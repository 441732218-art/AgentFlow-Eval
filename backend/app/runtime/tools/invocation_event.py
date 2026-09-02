# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool invocation event model for enterprise governance (in-memory only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InvocationStatus = Literal["success", "failed"]


@dataclass
class ToolInvocationEvent:
    """Minimal in-memory record of a single tool invocation."""

    execution_id: str
    tool_name: str
    started_at: float
    finished_at: float
    status: InvocationStatus | Literal["error"] = "success"
    error_type: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    duration_ms: float | None = None

    def __post_init__(self) -> None:
        if self.status == "error":
            self.status = "failed"
        if self.start_time is None:
            self.start_time = self.started_at
        if self.end_time is None:
            self.end_time = self.finished_at
        if self.duration_ms is None:
            self.duration_ms = max(0.0, (self.end_time - self.start_time) * 1000)
