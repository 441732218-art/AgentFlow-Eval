# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution persistence models (distinct from executor ``ExecutionResult``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ExecutionRecord:
    """Persisted execution lifecycle record managed by ``ExecutionStore``."""

    execution_id: str
    agent_id: str
    status: str
    output: Any | None
    error: str | None
    trace_reference: str | None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
