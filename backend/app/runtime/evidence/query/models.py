# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime evidence query models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from app.runtime.audit.models import AuditDecision


@dataclass(frozen=True)
class EvidenceQuery:
    """Immutable read-only query criteria for execution evidence."""

    execution_id: str | None = None
    agent_id: str | None = None
    correlation_id: str | None = None
    decision: AuditDecision | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int | None = None

    def with_updates(self, **changes: Any) -> EvidenceQuery:
        """Return a new query with updated fields."""
        return replace(self, **changes)
