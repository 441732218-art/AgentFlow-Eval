# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance evidence correlation store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.evidence_correlation.models import EvidenceCorrelation


class EvidenceCorrelationStore(Protocol):
    """Stores immutable governance evidence correlation records."""

    def save(self, correlation: EvidenceCorrelation) -> None:
        """Persist one evidence correlation record."""

    def get(self, correlation_id: str) -> EvidenceCorrelation | None:
        """Return one evidence correlation by identifier."""

    def list_by_execution(self, execution_id: str) -> list[EvidenceCorrelation]:
        """Return correlations recorded for an execution."""

    def list_all(self) -> list[EvidenceCorrelation]:
        """Return all stored evidence correlations."""

    def remove(self, correlation_id: str) -> None:
        """Remove one evidence correlation record."""

    def clear(self) -> None:
        """Remove all stored evidence correlations."""
