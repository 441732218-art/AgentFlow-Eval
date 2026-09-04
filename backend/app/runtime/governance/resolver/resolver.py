# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance effect resolver interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.execution.models import GovernanceExecutionEffect
from app.runtime.governance.resolver.models import GovernanceEffectResolution


class GovernanceEffectResolver(Protocol):
    """Resolves governance execution effects into normalized semantics."""

    def resolve(self, effect: GovernanceExecutionEffect) -> GovernanceEffectResolution:
        """Resolve one governance execution effect."""

    def get_resolution(self, resolution_id: str) -> GovernanceEffectResolution | None:
        """Return one recorded resolution by identifier."""

    def list_resolutions(self) -> list[GovernanceEffectResolution]:
        """Return all recorded effect resolutions."""

    def clear(self) -> None:
        """Remove all recorded effect resolutions."""
