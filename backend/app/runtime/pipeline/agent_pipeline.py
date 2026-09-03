# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent execution pipeline orchestrating runtime steps."""

from __future__ import annotations

import uuid
from typing import Any

from app.runtime.agent.lifecycle import complete_session, fail_session, start_session
from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.factory import ProductionRuntime
from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import attach_execution_context
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.execution.executor import StepExecutionContext, StepExecutor
from app.runtime.execution.sequential import SequentialExecutionStrategy
from app.runtime.execution.strategy import ExecutionStrategy
from app.runtime.pipeline.models import AgentExecutionResult, ExecutionStep
from app.runtime.pipeline.pipeline import ExecutionPipeline
from app.runtime.pipeline.steps import complete_step, create_step
from app.runtime.planning.default_planner import DefaultPlanner
from app.runtime.planning.planner import Planner


class _PipelineStepExecutor:
    """Adapts the runtime execution pipeline to the ``StepExecutor`` protocol."""

    def __init__(self, execution_pipeline: ExecutionPipeline, task: str) -> None:
        self._execution_pipeline = execution_pipeline
        self._task = task

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        if step.step_type == "execute":
            step_task = str(step.metadata.get("task", context.task))
            return self._execution_pipeline.run(context.runtime_context, step_task)
        raise RuntimeError(f"Unsupported planned step type: {step.step_type}")


class AgentExecutionPipeline:
    """Orchestrates agent execution steps through the existing runtime toolchain."""

    def __init__(
        self,
        production_runtime: ProductionRuntime,
        planner: Planner | None = None,
        strategy: ExecutionStrategy | None = None,
    ) -> None:
        self._production_runtime = production_runtime
        self._planner = planner or DefaultPlanner()
        self._strategy = strategy or SequentialExecutionStrategy()
        self._execution_pipeline = ExecutionPipeline(
            tool_execution_engine=production_runtime.tool_execution_engine,
        )

    def run(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext,
    ) -> AgentExecutionResult:
        """Run the agent execution pipeline and return a structured result."""
        steps: list[ExecutionStep] = []
        prepare_step = create_step("prepare", "agent.prepare")
        steps.append(prepare_step)

        session = start_session(
            agent_definition,
            context,
            task=task,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            execution_id=context.execution_id or uuid.uuid4().hex,
        )
        runtime_context = RuntimeContext(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            metadata=dict(context.metadata),
        )
        attach_execution_context(runtime_context, context)
        complete_step(prepare_step)

        plan = self._planner.create_plan(agent_definition, task, context)
        step_context = StepExecutionContext(runtime_context=runtime_context, task=task)
        step_executor = _PipelineStepExecutor(self._execution_pipeline, task)
        strategy_result = self._strategy.execute_plan(
            plan,
            step_context,
            step_executor,
        )

        for outcome in strategy_result.step_results:
            steps.append(outcome.step)

        if strategy_result.status == "COMPLETED":
            output = (
                strategy_result.step_results[-1].output
                if strategy_result.step_results
                else None
            )
            complete_session(
                session,
                context,
                agent_definition=agent_definition,
                output=output,
            )
            return AgentExecutionResult(
                execution_id=session.execution_id,
                agent_id=agent_definition.id,
                status="COMPLETED",
                output=output,
                steps=steps,
                metadata={"task": task, "plan_id": plan.plan_id},
            )

        fail_session(
            session,
            context,
            agent_definition=agent_definition,
            error=strategy_result.error or "execution strategy failed",
        )
        return AgentExecutionResult(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            status="FAILED",
            output=None,
            steps=steps,
            metadata={
                "task": task,
                "plan_id": plan.plan_id,
                "error_message": strategy_result.error,
            },
        )
