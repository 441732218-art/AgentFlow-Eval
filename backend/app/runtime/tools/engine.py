# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool execution engine — routes ``ToolDefinition`` to executor adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.runtime.governance.middleware import use_governance_lifecycle
from app.runtime.observability.events import RuntimeEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event
from app.runtime.policy.models import PolicyDecision, PolicyDeniedError
from app.runtime.policy.rules import allow_decision
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.executor_registry import (
    ToolExecutorRegistry,
    UnknownExecutorTypeError,
)

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext
    from app.runtime.invocation.guard import ToolInvocationGuard

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionResult:
    """Outcome of a single tool execution routed through an adapter."""

    tool_name: str
    executor_type: str
    output: Any


class ToolExecutionEngine:
    """Resolve ``executor_type`` and delegate execution to a registered adapter."""

    def __init__(
        self,
        adapter_registry: ToolExecutorRegistry | None = None,
        invocation_guard: ToolInvocationGuard | None = None,
    ) -> None:
        self.adapter_registry = adapter_registry or ToolExecutorRegistry()
        self.invocation_guard = invocation_guard

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any] | None = None,
        *,
        context: ExecutionContext | None = None,
    ) -> ToolExecutionResult:
        """Execute a tool definition via the matching executor adapter.

        Raises:
            TypeError: If ``tool_definition`` is not a ``ToolDefinition``.
            UnknownExecutorTypeError: If no adapter is registered for the type.
            PolicyDeniedError: If policy evaluation denies the tool execution.
        """
        if not isinstance(tool_definition, ToolDefinition):
            raise TypeError(
                f"Expected ToolDefinition, got {type(tool_definition).__name__}"
            )

        executor_type = tool_definition.executor_type
        adapter = self.adapter_registry.get(executor_type)
        if adapter is None:
            raise UnknownExecutorTypeError(executor_type)

        guard_handled_policy = False
        if self.invocation_guard is not None:
            from app.runtime.invocation.errors import ToolInvocationDeniedError
            from app.runtime.invocation.models import ToolInvocationContext

            invocation_context = ToolInvocationContext(
                tool_name=tool_definition.name,
                execution_id=context.execution_id if context is not None else "",
                agent_id=context.agent_id if context is not None else None,
            )
            guard_decision = self.invocation_guard.authorize(
                invocation_context,
                tool_definition,
                context,
            )
            if not guard_decision.allowed:
                self._publish_invocation_denied(
                    context,
                    tool_definition,
                    guard_decision,
                )
                raise ToolInvocationDeniedError(
                    tool_definition.name,
                    guard_decision.reason,
                )
            guard_handled_policy = self.invocation_guard.handles_policy_evaluation

        if use_governance_lifecycle(context):
            assert context is not None
            return context.governance_lifecycle.run_tool_execution(
                context=context,
                tool_definition=tool_definition,
                arguments=dict(arguments or {}),
                adapter=adapter,
                executor_type=executor_type,
            )

        decision = allow_decision("invocation_guard")
        if not guard_handled_policy:
            decision = self._evaluate_policy(context, tool_definition)
        if not decision.allowed:
            self._publish_policy_denied(context, tool_definition, decision)
            raise PolicyDeniedError(decision, tool_definition.name)

        output = adapter.execute(
            tool_definition,
            dict(arguments or {}),
            execution_context=context,
        )
        return ToolExecutionResult(
            tool_name=tool_definition.name,
            executor_type=executor_type,
            output=output,
        )

    @staticmethod
    def _evaluate_policy(
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
    ) -> PolicyDecision:
        if context is None or context.policy_engine is None:
            return allow_decision("default_allow")

        try:
            return context.policy_engine.evaluate(context, tool_definition)
        except Exception:
            logger.debug("runtime policy evaluation failed", exc_info=True)
            return allow_decision("policy_fallback_allow")

    @staticmethod
    def _publish_policy_denied(
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
        decision: PolicyDecision,
    ) -> None:
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

    @staticmethod
    def _publish_invocation_denied(
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
        decision: PolicyDecision,
    ) -> None:
        record_runtime_event(
            context,
            build_runtime_event(
                context,
                RuntimeEventType.TOOL_INVOCATION_DENIED,
                tool_name=tool_definition.name,
                status="denied",
                metadata={
                    "policy_name": decision.policy_name,
                    "reason": decision.reason,
                    **decision.metadata,
                },
            ),
        )
