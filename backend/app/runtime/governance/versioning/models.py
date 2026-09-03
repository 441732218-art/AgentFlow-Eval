# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance policy version models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

GovernancePolicyStatus = Literal["DRAFT", "ACTIVE", "DEPRECATED", "DISABLED"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GovernancePolicyVersion:
    """Immutable governance policy version metadata."""

    policy_id: str
    version: str
    name: str
    description: str | None = None
    status: GovernancePolicyStatus = "DRAFT"
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> GovernancePolicyVersion:
        """Return a new policy version with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)
