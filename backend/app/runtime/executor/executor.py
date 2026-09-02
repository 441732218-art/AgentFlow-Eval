# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Minimal Agent Executor skeleton."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from app.runtime.context import RuntimeContext
from app.runtime.memory import MemoryHook, MemoryProvider
from app.runtime.pipeline import ExecutionHook, ExecutionPipeline
from app.runtime.tools.registry import ToolRegistry
from app.runtime.tracing import TraceHook


def _build_default_pipeline(
    memory_provider: MemoryProvider | None = None,
) -> ExecutionPipeline:
    """Build the default pipeline with trace and optional memory hooks."""
    hooks: list[ExecutionHook] = [TraceHook()]
    if memory_provider is not None:
        hooks.append(MemoryHook(memory_provider))
    return ExecutionPipeline(hooks=hooks)


ExecutionStatus = Literal["SUCCESS", "FAILED"]


@dataclass
class ExecutionResult:
    """Outcome of a single AgentExecutor run (in-memory; no database)."""

    execution_id: str
    agent_id: str
    status: ExecutionStatus
    output: Any | None
    error: str | None


class AgentExecutor:
    """Runs a single agent request through the Runtime execution chain."""

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        pipeline: ExecutionPipeline | None = None,
        memory_provider: MemoryProvider | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.memory_provider = memory_provider
        self.pipeline = pipeline or _build_default_pipeline(memory_provider)

    def execute(
        self,
        agent_id: str,
        task: str,
        context: RuntimeContext | None = None,
    ) -> ExecutionResult:
        """Execute an agent task and return a structured result.

        Delegates execution to ``ExecutionPipeline``. Any internal exception
        is captured and returned as ``status="FAILED"``.
        """
        execution_id = ""
        try:
            if context is None:
                execution_id = self._new_execution_id()
                context = RuntimeContext(
                    execution_id=execution_id,
                    agent_id=agent_id,
                )
            else:
                execution_id = context.execution_id

            from app.runtime.executor.context_fields import ensure_execution_context

            ensure_execution_context(context)

            output = self.pipeline.run(context, task)

            return ExecutionResult(
                execution_id=execution_id,
                agent_id=agent_id,
                status="SUCCESS",
                output=output,
                error=None,
            )
        except Exception as exc:
            return ExecutionResult(
                execution_id=execution_id,
                agent_id=agent_id,
                status="FAILED",
                output=None,
                error=str(exc),
            )

    def _new_execution_id(self) -> str:
        return uuid.uuid4().hex
