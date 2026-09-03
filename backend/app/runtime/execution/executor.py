# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Step execution context and executor protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.runtime.context import RuntimeContext
    from app.runtime.pipeline.models import ExecutionStep


@dataclass
class StepExecutionContext:
    """Runtime context passed to step executors during plan execution."""

    runtime_context: RuntimeContext
    task: str


@runtime_checkable
class StepExecutor(Protocol):
    """Executes a single planned step without binding to a concrete engine."""

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        """Execute one plan step and return its output."""
