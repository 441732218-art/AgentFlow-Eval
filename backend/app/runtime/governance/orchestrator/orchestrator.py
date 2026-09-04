# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime orchestrator interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.orchestrator.models import (
    GovernanceExecutionRequest,
    GovernanceExecutionResult,
)


class GovernanceRuntimeOrchestrator(Protocol):
    """Coordinates governance components into orchestration results."""

    def execute(self, request: GovernanceExecutionRequest) -> GovernanceExecutionResult:
        """Coordinate governance components for one execution request."""
