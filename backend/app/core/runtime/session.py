# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Basic run session. Not Memory. Not RAG."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_session_id() -> str:
    return uuid.uuid4().hex


@dataclass
class AgentSession:
    """One Runtime invocation. Correlation only — no v1 Trace row."""

    session_id: str
    agent_id: str
    trace_id: str
    status: str = "created"
    created_at: datetime = field(default_factory=_utcnow)
    finished_at: datetime | None = None
    error_message: str = ""

    def mark_running(self) -> None:
        self.status = "running"

    def mark_completed(self) -> None:
        self.status = "completed"
        self.finished_at = _utcnow()

    def mark_failed(self, message: str = "") -> None:
        self.status = "failed"
        self.error_message = message
        self.finished_at = _utcnow()
