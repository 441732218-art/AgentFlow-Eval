# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance configuration registry."""

from __future__ import annotations

import threading

from app.runtime.governance.configuration.models import GovernanceConfiguration


class InMemoryGovernanceConfigurationRegistry:
    """Thread-safe in-memory governance configuration registry."""

    def __init__(self) -> None:
        self._configurations: dict[str, GovernanceConfiguration] = {}
        self._lock = threading.Lock()

    def register(self, configuration: GovernanceConfiguration) -> None:
        """Register or replace a governance configuration."""
        with self._lock:
            self._configurations[configuration.configuration_id] = configuration

    def get(self, configuration_id: str) -> GovernanceConfiguration | None:
        """Return one governance configuration by identifier."""
        with self._lock:
            configuration = self._configurations.get(configuration_id)
            if configuration is None:
                return None
            return configuration

    def list_all(self) -> list[GovernanceConfiguration]:
        """Return all registered governance configurations."""
        with self._lock:
            records = list(self._configurations.values())
        return sorted(records, key=lambda record: record.configuration_id)

    def remove(self, configuration_id: str) -> None:
        """Remove one governance configuration."""
        with self._lock:
            self._configurations.pop(configuration_id, None)

    def clear(self) -> None:
        """Remove all registered governance configurations."""
        with self._lock:
            self._configurations.clear()
