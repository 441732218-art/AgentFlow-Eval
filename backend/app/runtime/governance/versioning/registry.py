# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance policy version registry interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.versioning.models import GovernancePolicyVersion


class GovernancePolicyRegistry(Protocol):
    """Stores governance policy version metadata."""

    def register(self, policy_version: GovernancePolicyVersion) -> None:
        """Register or replace a policy version."""

    def get(self, policy_id: str, version: str) -> GovernancePolicyVersion | None:
        """Return one policy version by id and version."""

    def get_latest(self, policy_id: str) -> GovernancePolicyVersion | None:
        """Return the latest active policy version for a policy id."""

    def list_versions(self, policy_id: str) -> list[GovernancePolicyVersion]:
        """Return all versions registered for a policy id."""

    def remove(self, policy_id: str, version: str) -> None:
        """Remove one policy version."""
