# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime policy evaluation engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.runtime.policy.models import PolicyDecision
from app.runtime.policy.rules import allow_decision, evaluate_blocked_tool
from app.runtime.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext


class PolicyEngine(Protocol):
    """Evaluates whether a tool execution is permitted."""

    def evaluate(
        self,
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
    ) -> PolicyDecision:
        """Return a policy decision for the requested tool."""


class InMemoryPolicyEngine:
    """In-memory policy engine with optional blocked-tool deny list."""

    def __init__(
        self,
        *,
        blocked_tools: list[str] | None = None,
        policy_name: str = "in_memory",
    ) -> None:
        self._blocked_tools = frozenset(blocked_tools or [])
        self._policy_name = policy_name

    def evaluate(
        self,
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
    ) -> PolicyDecision:
        _ = context
        denied = evaluate_blocked_tool(
            tool_definition.name,
            blocked_tools=self._blocked_tools,
            policy_name=self._policy_name,
        )
        if denied is not None:
            return denied
        return allow_decision(self._policy_name)
