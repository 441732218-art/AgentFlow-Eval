# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent execution session model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SessionStatus = Literal["CREATED", "RUNNING", "COMPLETED", "FAILED"]


@dataclass
class ExecutionSession:
    """In-memory agent execution session (not persisted)."""

    execution_id: str
    agent_id: str
    status: SessionStatus = "CREATED"
    tenant_id: str | None = None
    user_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
