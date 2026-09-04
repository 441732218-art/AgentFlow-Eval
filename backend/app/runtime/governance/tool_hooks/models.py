# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool lifecycle governance hook models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ToolGovernanceHookContext:
    """Immutable governance view of a tool lifecycle hook event."""

    execution_id: str
    agent_id: str
    tool_name: str
    event_type: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> ToolGovernanceHookContext:
        """Return a new tool governance hook context with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
