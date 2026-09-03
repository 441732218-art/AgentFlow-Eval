# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime execution hook protocol."""

from __future__ import annotations

from app.runtime.hooks.models import RuntimeHookEvent


class RuntimeHook:
    """Optional lifecycle callbacks for runtime execution events."""

    def before_execution(self, event: RuntimeHookEvent) -> None:
        """Called before agent execution begins."""

    def after_execution(self, event: RuntimeHookEvent) -> None:
        """Called after agent execution completes successfully."""

    def before_step(self, event: RuntimeHookEvent) -> None:
        """Called before a planned step executes."""

    def after_step(self, event: RuntimeHookEvent) -> None:
        """Called after a planned step completes successfully."""

    def before_tool(self, event: RuntimeHookEvent) -> None:
        """Called before a tool invocation begins."""

    def after_tool(self, event: RuntimeHookEvent) -> None:
        """Called after a tool invocation completes successfully."""

    def on_failure(self, event: RuntimeHookEvent) -> None:
        """Called when execution, step, or tool failure occurs."""
