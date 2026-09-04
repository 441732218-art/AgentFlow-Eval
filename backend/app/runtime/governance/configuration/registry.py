# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance configuration registry interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.configuration.models import GovernanceConfiguration


class GovernanceConfigurationRegistry(Protocol):
    """Stores governance configuration records."""

    def register(self, configuration: GovernanceConfiguration) -> None:
        """Register or replace a governance configuration."""

    def get(self, configuration_id: str) -> GovernanceConfiguration | None:
        """Return one governance configuration by identifier."""

    def list_all(self) -> list[GovernanceConfiguration]:
        """Return all registered governance configurations."""

    def remove(self, configuration_id: str) -> None:
        """Remove one governance configuration."""
