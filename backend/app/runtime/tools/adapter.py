# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Executor adapter contract for tool execution routing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.runtime.tools.definition import ToolDefinition


class ToolExecutorAdapter(ABC):
    """Routes execution for a single ``executor_type`` (local, remote, etc.)."""

    executor_type: str

    @abstractmethod
    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: Any | None = None,
    ) -> Any:
        """Execute a tool capability with the supplied arguments."""
