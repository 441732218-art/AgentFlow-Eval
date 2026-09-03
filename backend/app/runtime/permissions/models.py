# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime permission models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class PermissionRequirement:
    """Immutable permission requirement for tool access."""

    permission: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> PermissionRequirement:
        """Return a new permission requirement with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
