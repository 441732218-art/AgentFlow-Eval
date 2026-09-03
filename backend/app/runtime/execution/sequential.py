# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Sequential execution strategy for agent plans."""

from __future__ import annotations

from app.runtime.execution.executor import StepExecutionContext, StepExecutor
from app.runtime.execution.models import ExecutionStrategyResult, StepExecutionOutcome
from app.runtime.pipeline.steps import complete_step, create_step, fail_step
from app.runtime.planning.models import ExecutionPlan


class SequentialExecutionStrategy:
    """Execute plan steps in order and stop on the first failure."""

    def execute_plan(
        self,
        plan: ExecutionPlan,
        context: StepExecutionContext,
        step_executor: StepExecutor,
    ) -> ExecutionStrategyResult:
        outcomes: list[StepExecutionOutcome] = []

        for planned_step in plan.steps:
            active_step = create_step(
                planned_step.name,
                planned_step.step_type,
                metadata=dict(planned_step.metadata),
            )
            try:
                output = step_executor.execute_step(active_step, context)
                complete_step(active_step)
                outcomes.append(
                    StepExecutionOutcome(step=active_step, output=output)
                )
            except Exception as exc:
                fail_step(active_step, exc)
                outcomes.append(
                    StepExecutionOutcome(step=active_step, output=None)
                )
                return ExecutionStrategyResult(
                    step_results=tuple(outcomes),
                    status="FAILED",
                    error=str(exc),
                )

        return ExecutionStrategyResult(
            step_results=tuple(outcomes),
            status="COMPLETED",
            error=None,
        )
