# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime policy decision models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicyDecision:
    """Outcome of a runtime policy evaluation."""

    allowed: bool
    policy_name: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PolicyDeniedError(Exception):
    """Raised when policy evaluation denies tool execution."""

    def __init__(self, decision: PolicyDecision, tool_name: str) -> None:
        self.decision = decision
        self.tool_name = tool_name
        message = decision.reason or f"Tool execution denied by {decision.policy_name}"
        super().__init__(message)
