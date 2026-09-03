# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance report store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.reporting.models import GovernanceReport


class ReportStore(Protocol):
    """Persists generated governance reports."""

    def create(self, report: GovernanceReport) -> None:
        """Create or replace a governance report."""

    def get(self, report_id: str) -> GovernanceReport | None:
        """Return one governance report by id."""

    def list_by_execution(self, execution_id: str) -> list[GovernanceReport]:
        """Return reports for an execution."""

    def delete(self, report_id: str) -> None:
        """Delete one governance report by id."""
