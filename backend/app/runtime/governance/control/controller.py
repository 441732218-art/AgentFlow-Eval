# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance control interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.control.models import GovernanceControlDecision
from app.runtime.governance.models import GovernanceDecision


class GovernanceController(Protocol):
    """Translates governance decisions into runtime control decisions."""

    def evaluate(self, decision: GovernanceDecision) -> GovernanceControlDecision:
        """Convert one governance decision into a control decision."""
