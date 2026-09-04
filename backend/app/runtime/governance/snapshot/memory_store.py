# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance evaluation snapshot store."""

from __future__ import annotations

import threading

from app.runtime.governance.snapshot.models import GovernanceSnapshot


class InMemoryGovernanceSnapshotStore:
    """Thread-safe in-memory governance snapshot store."""

    def __init__(self) -> None:
        self._snapshots: dict[str, GovernanceSnapshot] = {}
        self._lock = threading.Lock()

    def save(self, snapshot: GovernanceSnapshot) -> None:
        """Persist one governance snapshot."""
        with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> GovernanceSnapshot | None:
        """Return one governance snapshot by identifier."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def list_by_execution(self, execution_id: str) -> list[GovernanceSnapshot]:
        """Return snapshots recorded for an execution."""
        with self._lock:
            records = [
                snapshot
                for snapshot in self._snapshots.values()
                if snapshot.execution_id == execution_id
            ]
        return sorted(records, key=lambda snapshot: snapshot.created_at)

    def clear(self) -> None:
        """Remove all stored governance snapshots."""
        with self._lock:
            self._snapshots.clear()
