# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance decision routing interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.routing.models import GovernanceRouteRequest, GovernanceRouteResult


class GovernanceDecisionRouter(Protocol):
    """Routes governance outcomes into normalized routing decisions."""

    def route(self, request: GovernanceRouteRequest) -> GovernanceRouteResult:
        """Decide one governance routing outcome without executing runtime actions."""
