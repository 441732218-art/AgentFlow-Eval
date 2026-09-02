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


class AgentExecutionPipeline:
    """Orchestrates agent execution steps through the existing runtime toolchain."""

    def __init__(self, production_runtime: ProductionRuntime) -> None:
        self._production_runtime = production_runtime
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

        execute_step = create_step("execute", "agent.execute", metadata={"task": task})
        steps.append(execute_step)

        try:
            output = self._execution_pipeline.run(runtime_context, task)
            complete_step(execute_step)
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
                metadata={"task": task},
            )
        except Exception as exc:
            fail_step(execute_step, exc)
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
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
