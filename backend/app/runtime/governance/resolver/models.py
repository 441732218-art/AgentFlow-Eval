# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance effect resolver models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

GovernanceEffectResolutionType = Literal[
    "CONTINUE",
    "CONTINUE_WITH_WARNING",
    "BLOCK_REQUEST",
    "WAIT_APPROVAL",
]


@dataclass(frozen=True)
class GovernanceEffectResolution:
    """Immutable normalized resolution for a governance execution effect."""

    resolution_id: str
    effect_id: str
    resolution_type: GovernanceEffectResolutionType
    executable: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernanceEffectResolution:
        """Return a new effect resolution with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
