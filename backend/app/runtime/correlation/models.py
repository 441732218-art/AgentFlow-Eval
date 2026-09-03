# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime correlation context models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CorrelationContext:
    """Immutable runtime correlation node for execution relationships."""

    correlation_id: str
    execution_id: str
    parent_id: str | None
    span_id: str
    created_at: datetime = field(default_factory=_utc_now)

    def with_updates(self, **changes: Any) -> CorrelationContext:
        """Return a new correlation context with updated fields."""
        return replace(self, **changes)
