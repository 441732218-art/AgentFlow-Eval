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
from app.runtime.pipeline.models import AgentExecutionResult, ExecutionStep
from app.runtime.pipeline.pipeline import ExecutionPipeline
from app.runtime.pipeline.steps import complete_step, create_step, fail_step
from app.runtime.planning.default_planner import DefaultPlanner
from app.runtime.planning.planner import Planner


class AgentExecutionPipeline:
    """Orchestrates agent execution steps through the existing runtime toolchain."""

    def __init__(
        self,
        production_runtime: ProductionRuntime,
        planner: Planner | None = None,
    ) -> None:
        self._production_runtime = production_runtime
        self._planner = planner or DefaultPlanner()
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
        output: Any = None

        try:
            for planned_step in plan.steps:
                active_step = create_step(
                    planned_step.name,
                    planned_step.step_type,
                    metadata=dict(planned_step.metadata),
                )
                steps.append(active_step)
                output = self._execute_planned_step(
                    active_step,
                    runtime_context,
                    task,
                )
                complete_step(active_step)

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
        except Exception as exc:
            if steps and steps[-1].status == "RUNNING":
                fail_step(steps[-1], exc)
            fail_session(
                session,
                context,
                agent_definition=agent_definition,
                error=exc,
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
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )

    def _execute_planned_step(
        self,
        step: ExecutionStep,
        runtime_context: RuntimeContext,
        task: str,
    ) -> Any:
        if step.step_type == "execute":
            step_task = str(step.metadata.get("task", task))
            return self._execution_pipeline.run(runtime_context, step_task)
        raise RuntimeError(f"Unsupported planned step type: {step.step_type}")
