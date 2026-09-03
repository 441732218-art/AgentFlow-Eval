# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool invocation governance guard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.runtime.invocation.models import ToolInvocationContext
from app.runtime.policy.models import PolicyDecision
from app.runtime.policy.rules import allow_decision
from app.runtime.tool_registry.errors import ToolDisabledError, ToolNotFoundError
from app.runtime.tool_registry.registry import resolve_tool_capability
from app.runtime.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext
    from app.runtime.permissions.evaluator import PermissionEvaluator
    from app.runtime.tool_registry.registry import ToolRegistry


class ToolInvocationGuard:
    """Authorize tool invocations via capability and permission evaluation."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        permission_evaluator: PermissionEvaluator | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._permission_evaluator = permission_evaluator

    @property
    def handles_policy_evaluation(self) -> bool:
        return self._permission_evaluator is not None

    def authorize(
        self,
        invocation_context: ToolInvocationContext,
        tool_definition: ToolDefinition,
        execution_context: ExecutionContext | None = None,
    ) -> PolicyDecision:
        """Resolve capability and evaluate permissions before tool execution."""
        _ = invocation_context
        try:
            capability = resolve_tool_capability(
                self._tool_registry,
                tool_definition.name,
            )
        except ToolNotFoundError as exc:
            return PolicyDecision(
                allowed=False,
                policy_name="tool_capability_registry",
                reason=str(exc),
            )
        except ToolDisabledError as exc:
            return PolicyDecision(
                allowed=False,
                policy_name="tool_capability",
                reason=str(exc),
            )

        if self._permission_evaluator is None:
            return allow_decision("invocation_guard")

        return self._permission_evaluator.evaluate_tool_access(
            execution_context,
            capability,
        )

    def before_execute(
        self,
        invocation_context: ToolInvocationContext,
        tool_definition: ToolDefinition,
        execution_context: ExecutionContext | None = None,
    ) -> PolicyDecision:
        """Backward-compatible alias for ``authorize``."""
        return self.authorize(
            invocation_context,
            tool_definition,
            execution_context,
        )
