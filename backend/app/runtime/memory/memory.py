# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory implementation of ``MemoryProvider`` for tests and default runs."""

from __future__ import annotations

from typing import Any

from app.runtime.memory.provider import MemoryProvider


class InMemoryProvider(MemoryProvider):
    """Dict-backed memory provider (process-local; not shared across workers)."""

    def __init__(self) -> None:
        self._storage: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self._storage.get(key)

    def set(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def delete(self, key: str) -> None:
        self._storage.pop(key, None)

    def clear(self) -> None:
        self._storage.clear()
