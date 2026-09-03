# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Sequential execution strategy for agent plans."""

from __future__ import annotations

from app.runtime.execution.control import ExecutionController
from app.runtime.execution.executor import StepExecutionContext, StepExecutor
from app.runtime.execution.models import ExecutionStrategyResult, StepExecutionOutcome
from app.runtime.pipeline.steps import complete_step, create_step, fail_step
from app.runtime.planning.models import ExecutionPlan


class SequentialExecutionStrategy:
    """Execute plan steps in order and stop on the first failure."""

    def __init__(self, controller: ExecutionController | None = None) -> None:
        self._controller = controller or ExecutionController()

    def execute_plan(
        self,
        plan: ExecutionPlan,
        context: StepExecutionContext,
        step_executor: StepExecutor,
    ) -> ExecutionStrategyResult:
        outcomes: list[StepExecutionOutcome] = []
        last_error: str | None = None

        for planned_step in plan.steps:
            active_step = create_step(
                planned_step.name,
                planned_step.step_type,
                metadata=dict(planned_step.metadata),
            )
            control_outcome = self._controller.execute_step(
                active_step,
                context,
                step_executor,
            )
            if control_outcome.success:
                complete_step(active_step)
                outcomes.append(
                    StepExecutionOutcome(step=active_step, output=control_outcome.output)
                )
                continue

            fail_step(active_step, control_outcome.error)
            outcomes.append(
                StepExecutionOutcome(step=active_step, output=None)
            )
            last_error = control_outcome.error
            if control_outcome.stop_plan:
                return ExecutionStrategyResult(
                    step_results=tuple(outcomes),
                    status="FAILED",
                    error=last_error,
                )

        return ExecutionStrategyResult(
            step_results=tuple(outcomes),
            status="COMPLETED",
            error=last_error,
        )
