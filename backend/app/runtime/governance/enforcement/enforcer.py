# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance enforcement interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.enforcement.models import GovernanceAction
from app.runtime.governance.models import GovernanceDecision


class GovernanceEnforcer(Protocol):
    """Translates governance decisions into runtime enforcement actions."""

    def enforce(self, decision: GovernanceDecision) -> GovernanceAction:
        """Convert one governance decision into an enforcement action."""
