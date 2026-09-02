# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool execution engine — routes ``ToolDefinition`` to executor adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionResult:
    """Outcome of a single tool execution routed through an adapter."""

    tool_name: str
    executor_type: str
    output: Any


class ToolExecutionEngine:
    """Resolve ``executor_type`` and delegate execution to a registered adapter."""

    def __init__(self, adapter_registry: ToolExecutorRegistry | None = None) -> None:
        self.adapter_registry = adapter_registry or ToolExecutorRegistry()

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
