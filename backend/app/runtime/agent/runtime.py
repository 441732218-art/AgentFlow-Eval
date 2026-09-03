# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent runtime orchestration boundary."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, overload

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.session import ExecutionSession
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import ProductionRuntime
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.registry.registry import AgentNotFoundError

if TYPE_CHECKING:
    from app.runtime.audit.recorder import RuntimeAuditRecorder
    from app.runtime.permissions.evaluator import PermissionEvaluator
    from app.runtime.registry.registry import AgentRegistry
    from app.runtime.tool_registry.registry import ToolRegistry


class AgentDisabledError(RuntimeError):
    """Raised when execution is requested for a disabled agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent is disabled: {agent_id}")


@dataclass
class AgentRuntimeExecutionResult:
    """Outcome of a single ``AgentRuntime.execute`` invocation."""

    session: ExecutionSession
    output: Any | None = None
    error: str | None = None
    pipeline_result: Any | None = None


# Backward-compatible alias for existing callers and tests.
AgentExecutionResult = AgentRuntimeExecutionResult


class AgentRuntime:
    """Orchestrates agent execution using assembled production runtime components."""

    def __init__(
        self,
        production_runtime: ProductionRuntime,
        agent_registry: AgentRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
        permission_evaluator: PermissionEvaluator | None = None,
        audit_recorder: RuntimeAuditRecorder | None = None,
    ) -> None:
        self._production_runtime = production_runtime
        self._agent_registry = agent_registry
        self._tool_registry = tool_registry
        self._permission_evaluator = permission_evaluator
        self._audit_recorder = audit_recorder
        from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

        self._agent_pipeline = AgentExecutionPipeline(
            production_runtime,
            audit_recorder=audit_recorder,
        )

    @overload
    def execute(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext | None = None,
    ) -> AgentRuntimeExecutionResult: ...

    @overload
    def execute(
        self,
        agent_id: str,
        task: str,
        context: ExecutionContext | None = None,
    ) -> AgentRuntimeExecutionResult: ...

    def execute(
        self,
        agent_or_id: AgentDefinition | str,
        task: str,
        context: ExecutionContext | None = None,
    ) -> AgentRuntimeExecutionResult:
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

    def _validate_tool_capabilities(self, agent_definition: AgentDefinition) -> None:
        if self._tool_registry is None:
            return
        from app.runtime.tool_registry.registry import resolve_tool_capability

        for tool_name in agent_definition.tool_names:
            resolve_tool_capability(self._tool_registry, tool_name)

    def _validate_tool_permissions(
        self,
        agent_definition: AgentDefinition,
        execution_context: ExecutionContext,
    ) -> None:
        if self._permission_evaluator is None or self._tool_registry is None:
            return
        from app.runtime.observability.events import RuntimeEventType
        from app.runtime.observability.recording import build_runtime_event, record_runtime_event
        from app.runtime.policy.models import PolicyDeniedError
        from app.runtime.tool_registry.registry import resolve_tool_capability

        for tool_name in agent_definition.tool_names:
            capability = resolve_tool_capability(self._tool_registry, tool_name)
            decision = self._permission_evaluator.evaluate_tool_access(
                execution_context,
                capability,
            )
            if decision.allowed:
                continue
            record_runtime_event(
                execution_context,
                build_runtime_event(
                    execution_context,
                    RuntimeEventType.TOOL_PERMISSION_DENIED,
                    tool_name=tool_name,
                    status="denied",
                    metadata={
                        "policy_name": decision.policy_name,
                        "reason": decision.reason,
                    },
                ),
            )
            if self._audit_recorder is not None:
                self._audit_recorder.record_permission_event(
                    event_type=RuntimeEventType.TOOL_PERMISSION_DENIED,
                    execution_id=execution_context.execution_id,
                    agent_id=agent_definition.id,
                    correlation_id=execution_context.execution_id,
                    actor=execution_context.user_id or agent_definition.id,
                    resource=tool_name,
                    decision="DENY",
                    severity="WARNING",
                    metadata={
                        "policy_name": decision.policy_name,
                        "reason": decision.reason,
                    },
                )
            raise PolicyDeniedError(decision, tool_name)

    def _execute_definition(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext | None,
    ) -> AgentRuntimeExecutionResult:
        execution_context = context or create_execution_context(
            self._production_runtime,
            execution_id=uuid.uuid4().hex,
            agent_id=agent_definition.id,
        )
        self._validate_tool_capabilities(agent_definition)
        self._validate_tool_permissions(agent_definition, execution_context)
        pipeline_result = self._agent_pipeline.run(
            agent_definition,
            task,
            execution_context,
        )
        session = ExecutionSession(
            execution_id=pipeline_result.execution_id,
            agent_id=pipeline_result.agent_id,
            tenant_id=execution_context.tenant_id,
            user_id=execution_context.user_id,
            status="COMPLETED" if pipeline_result.status == "COMPLETED" else "FAILED",
            started_at=None,
            finished_at=None,
        )
        error = pipeline_result.metadata.get("error_message")
        return AgentRuntimeExecutionResult(
            session=session,
            output=pipeline_result.output,
            error=error if pipeline_result.status == "FAILED" else None,
            pipeline_result=pipeline_result,
        )
