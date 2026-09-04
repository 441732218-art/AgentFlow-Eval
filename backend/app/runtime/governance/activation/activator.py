# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime activation interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.activation.models import (
    GovernanceActivationRequest,
    GovernanceActivationResult,
)


class GovernanceRuntimeActivator(Protocol):
    """Decides whether governance runtime should be activated for an execution."""

    def activate(
        self,
        request: GovernanceActivationRequest,
    ) -> GovernanceActivationResult:
        """Return an activation decision without runtime execution."""
