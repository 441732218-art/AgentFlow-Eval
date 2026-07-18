# (c) 2026 AgentFlow-Eval
"""Delegate CachePort to existing multi-layer CacheClient."""

from __future__ import annotations

from typing import Any


class RedisL2CacheAdapter:
    """Wraps ``app.core.cache.client.get_cache_client`` (L1+L2)."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            from app.core.cache.client import get_cache

            self._client = get_cache()
        return self._client

    @property
    def backend_name(self) -> str:
        return "redis_l2"

    async def get(self, key: str) -> Any | None:
        client = self._get_client()
        return await client.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        client = self._get_client()
        await client.set(key, value, int(ttl or 60))

    async def delete(self, key: str) -> None:
        client = self._get_client()
        await client.delete(key)
