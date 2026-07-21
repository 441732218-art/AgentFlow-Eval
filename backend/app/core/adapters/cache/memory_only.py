# (c) 2026 AgentFlow-Eval
"""L1-only cache adapter for lite profile (no Redis)."""

from __future__ import annotations

from typing import Any

from app.core.cache.client import LocalMemoryCache


class MemoryOnlyCacheAdapter:
    def __init__(self, max_size: int = 2048, default_ttl: int = 60) -> None:
        self._l1 = LocalMemoryCache(max_size=max_size)
        self._default_ttl = default_ttl

    @property
    def backend_name(self) -> str:
        return "memory"

    async def get(self, key: str) -> Any | None:
        return await self._l1.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self._l1.set(
            key, value, int(ttl if ttl is not None else self._default_ttl)
        )

    async def delete(self, key: str) -> None:
        await self._l1.delete(key)
