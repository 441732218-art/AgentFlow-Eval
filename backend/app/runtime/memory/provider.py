# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Memory provider interface for Agent Runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryProvider(ABC):
    """Abstract key-value memory store for agent sessions."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return a stored value, or ``None`` if the key is missing."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store a value under ``key``."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a stored value."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored values."""
