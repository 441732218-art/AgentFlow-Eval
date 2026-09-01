# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution pipeline orchestrating Runtime lifecycle steps."""

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import get_tool_definition
from app.runtime.pipeline.hooks import ExecutionHook
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.tools.engine import ToolExecutionEngine


class ExecutionPipeline:
    """Orchestrates before_execute → execute_step → after_execute."""

    def __init__(
        self,
        hooks: list[ExecutionHook] | None = None,
        tool_execution_engine: ToolExecutionEngine | None = None,
    ) -> None:
        self.hooks: list[ExecutionHook] = list(hooks or [])
        self.tool_execution_engine = tool_execution_engine

    def run(self, context: RuntimeContext, task: str) -> Any:
        """Run the execution pipeline and return the step output."""
        self._before_execute(context, task)
        result = self._execute_step(context, task)
        self._after_execute(context, result)
        return result

    def _before_execute(self, context: RuntimeContext, task: str) -> None:
        for hook in self.hooks:
            hook.before_execute(context, task)

    def _execute_step(self, context: RuntimeContext, task: str) -> Any:
        if get_tool_definition(context) is not None:
            return execute_tool_via_engine(context, self.tool_execution_engine)
        _ = task
        return "pipeline execution completed"

    def _after_execute(self, context: RuntimeContext, result: Any) -> None:
        for hook in self.hooks:
            hook.after_execute(context, result)
