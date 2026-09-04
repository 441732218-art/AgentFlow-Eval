# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class GovernanceConfigurationScope:
    """Immutable governance configuration scope descriptor."""

    scope_id: str
    agent_id: str | None = None
    tenant_id: str | None = None
    tags: tuple[str, ...] = ()

    def with_updates(self, **changes: Any) -> GovernanceConfigurationScope:
        """Return a new configuration scope with updated fields."""
        if "tags" in changes:
            changes["tags"] = tuple(changes["tags"])
        return replace(self, **changes)


@dataclass(frozen=True)
class GovernanceConfiguration:
    """Immutable governance configuration record."""

    configuration_id: str
    name: str
    description: str
    enabled: bool
    environment: str
    metadata: dict[str, Any] = field(default_factory=dict)
    scope: GovernanceConfigurationScope | None = None

    def with_updates(self, **changes: Any) -> GovernanceConfiguration:
        """Return a new governance configuration with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
