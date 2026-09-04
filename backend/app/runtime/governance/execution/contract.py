# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance execution contract interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.execution.models import (
    GovernanceExecutionEffect,
    GovernanceExecutionRecord,
)


class GovernanceExecutionContract(Protocol):
    """Records governance execution effects without modifying runtime behavior."""

    def execute(self, effect: GovernanceExecutionEffect) -> GovernanceExecutionRecord:
        """Observe one governance execution effect."""

    def get_execution(self, effect_id: str) -> GovernanceExecutionRecord | None:
        """Return one recorded governance execution by effect identifier."""

    def list_executions(self) -> list[GovernanceExecutionRecord]:
        """Return all recorded governance executions."""

    def clear(self) -> None:
        """Remove all recorded governance executions."""
