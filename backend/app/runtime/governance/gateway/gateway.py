# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance decision gateway interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.gateway.models import GovernanceGateRequest, GovernanceGateResult


class GovernanceDecisionGateway(Protocol):
    """Evaluates governance control outcomes at the runtime decision gateway."""

    def evaluate(self, request: GovernanceGateRequest) -> GovernanceGateResult:
        """Evaluate one gateway request and return a gate result."""
