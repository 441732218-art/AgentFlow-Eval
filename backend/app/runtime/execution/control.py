# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution controller applying retry and failure policies to step execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.runtime.execution.failure import DefaultFailurePolicy, FailurePolicy
from app.runtime.execution.retry import DefaultRetryPolicy, RetryPolicy

if TYPE_CHECKING:
    from app.runtime.execution.executor import StepExecutionContext, StepExecutor
    from app.runtime.pipeline.models import ExecutionStep


@dataclass(frozen=True)
class StepControlOutcome:
    """Immutable outcome from a controlled step execution."""

    success: bool
    output: Any | None = None
    error: str | None = None
    attempts: int = 1
    stop_plan: bool = False


class ExecutionController:
    """Executes one step through a ``StepExecutor`` with retry and failure policies."""

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
    ) -> None:
        self._retry_policy = retry_policy or DefaultRetryPolicy()
        self._failure_policy = failure_policy or DefaultFailurePolicy()

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
        step_executor: StepExecutor,
    ) -> StepControlOutcome:
        """Execute one step with retry handling and failure policy evaluation."""
        attempt = 0
        last_error: Exception | None = None

        while True:
            attempt += 1
            try:
                output = step_executor.execute_step(step, context)
                return StepControlOutcome(
                    success=True,
                    output=output,
                    attempts=attempt,
                    stop_plan=False,
                )
            except Exception as exc:
                last_error = exc
                if not self._retry_policy.should_retry(attempt, exc):
                    break

        stop_plan = self._failure_policy.should_stop_plan()
        return StepControlOutcome(
            success=False,
            output=None,
            error=str(last_error) if last_error is not None else "step execution failed",
            attempts=attempt,
            stop_plan=stop_plan,
        )
