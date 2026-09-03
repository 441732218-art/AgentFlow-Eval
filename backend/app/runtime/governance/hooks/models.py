# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime hook adapter models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class GovernanceHookContext:
    """Immutable governance view of a runtime hook event."""

    execution_id: str
    agent_id: str
    event_type: str
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceHookContext:
        """Return a new governance hook context with updated fields."""
        if "payload" in changes:
            changes["payload"] = dict(changes["payload"])
        return replace(self, **changes)
