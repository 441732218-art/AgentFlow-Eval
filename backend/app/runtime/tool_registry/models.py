# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool capability models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class ToolCapability:
    """Immutable runtime tool capability descriptor."""

    tool_name: str
    version: str = "1.0"
    description: str = ""
    capability_tags: tuple[str, ...] = ()
    permission_scope: tuple[str, ...] = ()
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> ToolCapability:
        """Return a new tool capability with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        if "capability_tags" in changes:
            changes["capability_tags"] = tuple(changes["capability_tags"])
        if "permission_scope" in changes:
            changes["permission_scope"] = tuple(changes["permission_scope"])
        return replace(self, **changes)
