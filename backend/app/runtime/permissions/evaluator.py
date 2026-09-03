# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool permission evaluation coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.runtime.permissions.binding import ToolPermissionBinding, binding_from_capability
from app.runtime.policy.models import PolicyDecision
from app.runtime.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext
    from app.runtime.policy.engine import PolicyEngine
    from app.runtime.tool_registry.models import ToolCapability


class PermissionEvaluator:
    """Coordinate tool capability metadata with runtime policy evaluation."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        bindings: dict[str, ToolPermissionBinding] | None = None,
    ) -> None:
        self._policy_engine = policy_engine
        self._bindings = dict(bindings or {})

    def evaluate_tool_access(
        self,
        context: ExecutionContext | None,
        tool_capability: ToolCapability,
    ) -> PolicyDecision:
        """Evaluate whether ``tool_capability`` is allowed for execution."""
        if not tool_capability.enabled:
            return PolicyDecision(
                allowed=False,
                policy_name="tool_capability",
                reason=f"Tool capability is disabled: {tool_capability.tool_name}",
            )

        binding = self._bindings.get(tool_capability.tool_name)
        if binding is None:
            binding = binding_from_capability(tool_capability)

        if binding.permissions and not tool_capability.permission_scope:
            return PolicyDecision(
                allowed=False,
                policy_name="tool_permission_binding",
                reason=f"Missing required permissions for {tool_capability.tool_name}",
            )

        tool_definition = ToolDefinition(
            name=tool_capability.tool_name,
            description=tool_capability.description or tool_capability.tool_name,
            executor_type="local",
            metadata={
                "version": tool_capability.version,
                "permission_scope": list(tool_capability.permission_scope),
                "required_permissions": [
                    requirement.permission for requirement in binding.permissions
                ],
            },
        )
        return self._policy_engine.evaluate(context, tool_definition)
