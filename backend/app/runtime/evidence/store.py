# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime evidence persistence interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.evidence.models import ExecutionEvidence


class EvidenceStore(Protocol):
    """Persists aggregated runtime governance evidence."""

    def save(self, evidence: ExecutionEvidence) -> None:
        """Persist one execution evidence record."""

    def get(self, evidence_id: str) -> ExecutionEvidence | None:
        """Return one evidence record by id."""

    def get_by_execution(self, execution_id: str) -> ExecutionEvidence | None:
        """Return the latest evidence record for an execution."""

    def list_by_agent(self, agent_id: str) -> list[ExecutionEvidence]:
        """Return evidence records for an agent."""

    def delete(self, evidence_id: str) -> None:
        """Delete one evidence record by id."""
