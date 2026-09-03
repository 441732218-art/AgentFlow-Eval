# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance policy version registry."""

from __future__ import annotations

import threading

from app.runtime.governance.versioning.models import GovernancePolicyVersion


class InMemoryGovernancePolicyRegistry:
    """Thread-safe in-memory governance policy version registry."""

    def __init__(self) -> None:
        self._versions: dict[str, dict[str, GovernancePolicyVersion]] = {}
        self._lock = threading.Lock()

    def register(self, policy_version: GovernancePolicyVersion) -> None:
        with self._lock:
            policy_versions = self._versions.setdefault(policy_version.policy_id, {})
            policy_versions[policy_version.version] = policy_version

    def get(self, policy_id: str, version: str) -> GovernancePolicyVersion | None:
        with self._lock:
            return self._versions.get(policy_id, {}).get(version)

    def get_latest(self, policy_id: str) -> GovernancePolicyVersion | None:
        with self._lock:
            versions = list(self._versions.get(policy_id, {}).values())
        active_versions = [version for version in versions if version.status == "ACTIVE"]
        if not active_versions:
            return None
        stable_versions = [
            version for version in active_versions if "-" not in version.version
        ]
        candidates = stable_versions or active_versions
        return max(candidates, key=_version_sort_key)

    def list_versions(self, policy_id: str) -> list[GovernancePolicyVersion]:
        with self._lock:
            versions = list(self._versions.get(policy_id, {}).values())
        return sorted(versions, key=_version_sort_key)

    def remove(self, policy_id: str, version: str) -> None:
        with self._lock:
            policy_versions = self._versions.get(policy_id)
            if policy_versions is None:
                return
            policy_versions.pop(version, None)
            if not policy_versions:
                self._versions.pop(policy_id, None)


def _version_sort_key(policy_version: GovernancePolicyVersion) -> tuple[int, ...]:
    return _parse_semver(policy_version.version)


def _parse_semver(version: str) -> tuple[int, ...]:
    """Parse a semantic version string into a comparable numeric tuple."""
    core, _, prerelease = version.partition("-")
    numbers: list[int] = []
    for segment in core.split("."):
        digits = "".join(character for character in segment if character.isdigit())
        numbers.append(int(digits or "0"))
    while len(numbers) < 3:
        numbers.append(0)
    release_rank = 1 if not prerelease else 0
    return tuple(numbers[:3] + [release_rank])
