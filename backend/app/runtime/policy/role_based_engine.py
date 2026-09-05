# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Role-aware policy engine — optional alternative to ``InMemoryPolicyEngine``.

NOTE: Role extraction keys (``metadata['roles']`` / ``metadata['role']``) are a
provisional convention and are NOT yet aligned with the ``app.core.rbac`` role
model. This must be resolved before wiring this engine into the HTTP production
path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.runtime.policy.models import PolicyDecision
from app.runtime.policy.rules import allow_decision, evaluate_blocked_tool
from app.runtime.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext

# Provisional keys — no repo-wide convention exists yet (see module docstring / audit report).
_ROLE_METADATA_KEY = "role"
_ROLES_METADATA_KEY = "roles"


def _normalize_role_values(raw: Any) -> tuple[str, ...]:
    """Normalize role metadata values into non-empty strings."""
    if raw is None:
        return ()
    if isinstance(raw, str):
        value = raw.strip()
        return (value,) if value else ()
    if isinstance(raw, (list, tuple, set, frozenset)):
        values: list[str] = []
        for item in raw:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                values.append(text)
        return tuple(values)
    text = str(raw).strip()
    return (text,) if text else ()


def extract_context_roles(context: ExecutionContext | None) -> frozenset[str]:
    """Extract caller roles from ``ExecutionContext.metadata``.

    Reads provisional keys ``roles`` (preferred, list or str) then ``role`` (str).
    No production caller convention is established in ``backend/app/`` yet.
    """
    if context is None:
        return frozenset()

    metadata = context.metadata or {}
    roles: list[str] = []
    roles.extend(_normalize_role_values(metadata.get(_ROLES_METADATA_KEY)))
    roles.extend(_normalize_role_values(metadata.get(_ROLE_METADATA_KEY)))
    return frozenset(roles)


def _permission_scope_from_tool(tool_definition: ToolDefinition) -> tuple[str, ...]:
    raw = (tool_definition.metadata or {}).get("permission_scope", ())
    if isinstance(raw, str):
        value = raw.strip()
        return (value,) if value else ()
    if isinstance(raw, (list, tuple, set, frozenset)):
        return _normalize_role_values(list(raw))
    return ()


class RoleBasedPolicyEngine:
    """Policy engine that enforces ``permission_scope`` against caller roles.

    Evaluation order:
    1. ``blocked_tools`` deny list (explicit override — safety net)
    2. Empty ``permission_scope`` → allow (backward compatible)
    3. Non-empty ``permission_scope`` → allow when caller role intersects scope
    """

    def __init__(
        self,
        *,
        blocked_tools: list[str] | None = None,
        policy_name: str = "role_based",
    ) -> None:
        self._blocked_tools = frozenset(blocked_tools or [])
        self._policy_name = policy_name

    def evaluate(
        self,
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
    ) -> PolicyDecision:
        denied = evaluate_blocked_tool(
            tool_definition.name,
            blocked_tools=self._blocked_tools,
            policy_name=self._policy_name,
        )
        if denied is not None:
            return denied

        permission_scope = _permission_scope_from_tool(tool_definition)
        if not permission_scope:
            return allow_decision(self._policy_name)

        caller_roles = extract_context_roles(context)
        if caller_roles.intersection(permission_scope):
            return allow_decision(self._policy_name)

        required = ", ".join(sorted(permission_scope))
        held = ", ".join(sorted(caller_roles)) if caller_roles else "(none)"
        return PolicyDecision(
            allowed=False,
            policy_name=self._policy_name,
            reason=(
                f"Role not permitted for {tool_definition.name}: "
                f"required one of [{required}], caller has [{held}]"
            ),
            metadata={
                "tool_name": tool_definition.name,
                "permission_scope": list(permission_scope),
                "caller_roles": sorted(caller_roles),
            },
        )
