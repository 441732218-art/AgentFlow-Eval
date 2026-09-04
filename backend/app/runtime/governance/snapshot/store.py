# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance evaluation snapshot store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.snapshot.models import GovernanceSnapshot


class SnapshotStore(Protocol):
    """Stores immutable governance evaluation snapshots."""

    def save(self, snapshot: GovernanceSnapshot) -> None:
        """Persist one governance snapshot."""

    def get(self, snapshot_id: str) -> GovernanceSnapshot | None:
        """Return one governance snapshot by identifier."""

    def list_by_execution(self, execution_id: str) -> list[GovernanceSnapshot]:
        """Return snapshots recorded for an execution."""

    def clear(self) -> None:
        """Remove all stored governance snapshots."""
