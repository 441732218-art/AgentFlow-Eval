# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime decision adapter interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.runtime_adapter.models import (
    GovernanceRuntimeDecisionRequest,
    GovernanceRuntimeDecisionResult,
)


class GovernanceRuntimeDecisionAdapter(Protocol):
    """Adapts normalized governance decisions into execution effect semantics."""

    def adapt(self, request: GovernanceRuntimeDecisionRequest) -> GovernanceRuntimeDecisionResult:
        """Adapt one governance decision request into runtime effect semantics."""
