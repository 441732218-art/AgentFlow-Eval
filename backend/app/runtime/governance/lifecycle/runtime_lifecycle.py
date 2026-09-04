# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Unified runtime governance lifecycle coordinator."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from app.runtime.observability.events import RuntimeEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event
from app.runtime.policy.models import PolicyDecision, PolicyDeniedError
from app.runtime.policy.rules import allow_decision
from app.runtime.tools.invocation_event import ToolInvocationEvent

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext
    from app.runtime.policy.engine import PolicyEngine
    from app.runtime.tools.adapter import ToolExecutorAdapter
    from app.runtime.tools.definition import ToolDefinition
    from app.runtime.tools.engine import ToolExecutionResult

logger = logging.getLogger(__name__)


class RuntimeGovernanceLifecycle:
    """Coordinates policy, observation, publishing, and audit for tool execution."""

    def execution_started(self, context: ExecutionContext, task: str) -> None:
        """Publish an execution.started governance event."""
        record_runtime_event(
            context,
            build_runtime_event(
                context,
                RuntimeEventType.EXECUTION_STARTED,
                metadata={"task": task},
            ),
        )

    def before_tool_execution(
        self,
        context: ExecutionContext,
        tool_definition: ToolDefinition,
        *,
        start_time: float | None = None,
    ) -> float:
        """Record tool.started before adapter invocation."""
        started_at = start_time if start_time is not None else time.monotonic()
        record_runtime_event(
            context,
            build_runtime_event(
                context,
                RuntimeEventType.TOOL_STARTED,
                tool_name=tool_definition.name,
                metadata={"executor_type": tool_definition.executor_type},
            ),
        )
        return started_at

    def evaluate_policy(
        self,
        context: ExecutionContext,
        tool_definition: ToolDefinition,
    ) -> PolicyDecision:
        """Evaluate tool policy using the context-bound policy engine."""
        policy_engine: PolicyEngine | None = context.policy_engine
        if policy_engine is None:
            return allow_decision("default_allow")
        try:
            return policy_engine.evaluate(context, tool_definition)
        except Exception:
            logger.debug("runtime policy evaluation failed", exc_info=True)
            return allow_decision("policy_fallback_allow")

    def on_policy_denied(
        self,
        context: ExecutionContext,
        tool_definition: ToolDefinition,
        decision: PolicyDecision,
    ) -> None:
        """Record a unified tool.policy.denied governance event."""
        record_runtime_event(
            context,
            build_runtime_event(
                context,
                RuntimeEventType.TOOL_POLICY_DENIED,
                tool_name=tool_definition.name,
                status="denied",
                metadata={
                    "policy_name": decision.policy_name,
                    "reason": decision.reason,
                    **decision.metadata,
                },
            ),
        )

    def after_tool_success(
        self,
        context: ExecutionContext,
        tool_definition: ToolDefinition,
        *,
        start_time: float,
        output: Any,
    ) -> None:
        """Record tool.completed with duration and safe result metadata."""
        end_time = time.monotonic()
        invocation = ToolInvocationEvent(
            execution_id=context.execution_id,
            tool_name=tool_definition.name,
            started_at=start_time,
            finished_at=end_time,
            status="success",
        )
        record_runtime_event(
            context,
            build_runtime_event(
                context,
                RuntimeEventType.TOOL_COMPLETED,
                tool_name=tool_definition.name,
                status="success",
                duration_ms=invocation.duration_ms,
                metadata={
                    "executor_type": tool_definition.executor_type,
                    "output_type": type(output).__name__,
                },
            ),
        )

    def after_tool_failure(
        self,
        context: ExecutionContext,
        tool_definition: ToolDefinition,
        *,
        start_time: float,
        exc: BaseException,
    ) -> None:
        """Record tool.failed with duration and error metadata."""
        end_time = time.monotonic()
        invocation = ToolInvocationEvent(
            execution_id=context.execution_id,
            tool_name=tool_definition.name,
            started_at=start_time,
            finished_at=end_time,
            status="failed",
            error_type=type(exc).__name__,
        )
        record_runtime_event(
            context,
            build_runtime_event(
                context,
                RuntimeEventType.TOOL_FAILED,
                tool_name=tool_definition.name,
                status="failed",
                duration_ms=invocation.duration_ms,
                metadata={
                    "executor_type": tool_definition.executor_type,
                    "error_type": invocation.error_type,
                    "error_message": str(exc),
                },
            ),
        )

    def run_tool_execution(
        self,
        *,
        context: ExecutionContext,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        adapter: ToolExecutorAdapter,
        executor_type: str,
    ) -> ToolExecutionResult:
        """Run the governed tool lifecycle and return the execution result."""
        from app.runtime.tools.engine import ToolExecutionResult

        start_time = self.before_tool_execution(context, tool_definition)
        decision = self.evaluate_policy(context, tool_definition)
        if not decision.allowed:
            self.on_policy_denied(context, tool_definition, decision)
            raise PolicyDeniedError(decision, tool_definition.name)

        try:
            output = adapter.execute(
                tool_definition,
                arguments,
                execution_context=context,
            )
        except Exception as exc:
            self.after_tool_failure(
                context,
                tool_definition,
                start_time=start_time,
                exc=exc,
            )
            raise

        self.after_tool_success(
            context,
            tool_definition,
            start_time=start_time,
            output=output,
        )
        return ToolExecutionResult(
            tool_name=tool_definition.name,
            executor_type=executor_type,
            output=output,
        )
