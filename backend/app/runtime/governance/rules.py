# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance rule evaluation protocol."""

from __future__ import annotations

from typing import Protocol

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.models import GovernanceDecision


class GovernanceRule(Protocol):
    """Evaluates execution evidence and returns a governance decision."""

    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        """Evaluate evidence and return one governance decision."""
