# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent runtime orchestration boundary."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, overload

from app.runtime.agent.lifecycle import complete_session, fail_session, start_session
from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.session import ExecutionSession
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import ProductionRuntime
from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import attach_execution_context
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.registry.registry import AgentNotFoundError

if TYPE_CHECKING:
    from app.runtime.registry.registry import AgentRegistry


class AgentDisabledError(RuntimeError):
    """Raised when execution is requested for a disabled agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent is disabled: {agent_id}")


@dataclass
class AgentExecutionResult:
    """Outcome of a single ``AgentRuntime.execute`` invocation."""

    session: ExecutionSession
    output: Any | None = None
    error: str | None = None


class AgentRuntime:
    """Orchestrates agent execution using assembled production runtime components."""

    def __init__(
        self,
        production_runtime: ProductionRuntime,
        agent_registry: AgentRegistry | None = None,
    ) -> None:
        self._production_runtime = production_runtime
        self._agent_registry = agent_registry
        self._pipeline = ExecutionPipeline(
            tool_execution_engine=production_runtime.tool_execution_engine,
        )

    @overload
    def execute(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext | None = None,
    ) -> AgentExecutionResult: ...

    @overload
    def execute(
        self,
        agent_id: str,
        task: str,
        context: ExecutionContext | None = None,
    ) -> AgentExecutionResult: ...

    def execute(
        self,
        agent_or_id: AgentDefinition | str,
        task: str,
        context: ExecutionContext | None = None,
    ) -> AgentExecutionResult:
        """Run an agent task through the existing runtime orchestration boundary."""
        if isinstance(agent_or_id, str):
            agent_definition = self._resolve_agent(agent_or_id)
        else:
            agent_definition = agent_or_id
        return self._execute_definition(agent_definition, task, context)

    def _resolve_agent(self, agent_id: str) -> AgentDefinition:
        if self._agent_registry is None:
            raise AgentNotFoundError(agent_id)
        agent_definition = self._agent_registry.get(agent_id)
        if agent_definition is None:
            raise AgentNotFoundError(agent_id)
        if not agent_definition.enabled:
            raise AgentDisabledError(agent_id)
        return agent_definition

    def _execute_definition(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext | None,
    ) -> AgentExecutionResult:
        execution_context = context or create_execution_context(
            self._production_runtime,
            execution_id=uuid.uuid4().hex,
            agent_id=agent_definition.id,
        )
        session = start_session(
            agent_definition,
            execution_context,
            task=task,
            tenant_id=execution_context.tenant_id,
            user_id=execution_context.user_id,
            execution_id=execution_context.execution_id,
        )

        runtime_context = RuntimeContext(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            metadata=dict(execution_context.metadata),
        )
        attach_execution_context(runtime_context, execution_context)

        try:
            output = self._pipeline.run(runtime_context, task)
            complete_session(
                session,
                execution_context,
                agent_definition=agent_definition,
                output=output,
            )
            return AgentExecutionResult(session=session, output=output, error=None)
        except Exception as exc:
            fail_session(
                session,
                execution_context,
                agent_definition=agent_definition,
                error=exc,
            )
            return AgentExecutionResult(
                session=session,
                output=None,
                error=str(exc),
            )
