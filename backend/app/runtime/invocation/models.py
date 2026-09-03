# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool invocation context models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class ToolInvocationContext:
    """Immutable context for a single tool invocation attempt."""

    tool_name: str
    execution_id: str
    agent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> ToolInvocationContext:
        """Return a new invocation context with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
