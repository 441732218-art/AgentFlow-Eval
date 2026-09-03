# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution strategy protocol for plan execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.runtime.execution.executor import StepExecutor
from app.runtime.execution.models import ExecutionStrategyResult

if TYPE_CHECKING:
    from app.runtime.execution.executor import StepExecutionContext
    from app.runtime.planning.models import ExecutionPlan


@runtime_checkable
class ExecutionStrategy(Protocol):
    """Executes an ``ExecutionPlan`` using a supplied step executor."""

    def execute_plan(
        self,
        plan: ExecutionPlan,
        context: StepExecutionContext,
        step_executor: StepExecutor,
    ) -> ExecutionStrategyResult:
        """Execute a plan and return aggregated step results."""
