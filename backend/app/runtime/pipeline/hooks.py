# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution lifecycle hooks for the Runtime pipeline."""

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext


class ExecutionHook:
    """Base hook for pipeline lifecycle events (trace, memory, security, etc.)."""

    def before_execute(self, context: RuntimeContext, task: str) -> None:
        """Called before the execute step runs."""

    def after_execute(self, context: RuntimeContext, result: Any) -> None:
        """Called after the execute step completes successfully."""
