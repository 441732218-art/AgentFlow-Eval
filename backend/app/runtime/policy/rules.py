# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Built-in runtime policy rules."""

from __future__ import annotations

from app.runtime.policy.models import PolicyDecision

BLOCKED_TOOL_RULE = "blocked_tool"


def evaluate_blocked_tool(
    tool_name: str,
    *,
    blocked_tools: frozenset[str],
    policy_name: str,
) -> PolicyDecision | None:
    """Return a deny decision when ``tool_name`` is blocked."""
    if tool_name not in blocked_tools:
        return None
    return PolicyDecision(
        allowed=False,
        policy_name=policy_name,
        reason=f"tool blocked by policy: {tool_name}",
        metadata={"tool_name": tool_name, "rule": BLOCKED_TOOL_RULE},
    )


def allow_decision(policy_name: str) -> PolicyDecision:
    """Return a default allow decision."""
    return PolicyDecision(allowed=True, policy_name=policy_name)
