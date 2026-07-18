# (c) 2026 AgentFlow-Eval
"""Two-level cache client: L1 in-process + L2 Redis (redis.asyncio)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class _L1Entry:
    value: Any
    expires_at: float


class LocalMemoryCache:
    """Bounded TTL cache for L1 (process-local)."""

    def __init__(self, max_size: int = 2048) -> None:
        self._max_size = max(16, max_size)
        self._data: OrderedDict[str, _L1Entry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            # expires_at == 0 means no expiry; >0 is absolute monotonic deadline
            if entry.expires_at > 0 and entry.expires_at < time.monotonic():
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            exp = time.monotonic() + max(1, int(ttl)) if ttl else 0.0
            self._data[key] = _L1Entry(value=value, expires_at=exp)
            self._data.move_to_end(key)
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        async with self._lock:
            keys = [k for k in self._data if k.startswith(prefix) or k == prefix]
            for k in keys:
                self._data.pop(k, None)
            return len(keys)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()


class CacheClient:
    """Cache-aside / write-through client with L1 memory + L2 Redis.

    Redis failures are swallowed so the API remains available (degraded).
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        l1_max_size: int = 2048,
        use_l1: bool = True,
    ) -> None:
        self.enabled = enabled
        self.use_l1 = use_l1
        self.l1 = LocalMemoryCache(max_size=l1_max_size)

    def _metrics_enabled(self) -> bool:
        try:
            from app.config import settings

            return bool(getattr(settings, "CACHE_ENABLED", True))
        except Exception:
            return self.enabled

    async def get(self, key: str) -> Any | None:
        """Cache-aside read: L1 → L2 → miss."""
        if not self._metrics_enabled():
            return None
        # L1
        if self.use_l1:
            val = await self.l1.get(key)
            if val is not None:
                self._hit("l1")
                return val
        # L2 Redis
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            raw = await r.get(key)
            if raw is None:
                self._miss()
                return None
            val = json.loads(raw)
            if self.use_l1:
                # populate L1 with remaining TTL if available
                ttl = await r.ttl(key)
                await self.l1.set(key, val, ttl if ttl and ttl > 0 else 60)
            self._hit("l2")
            return val
        except Exception as exc:
            logger.debug("cache get failed key=%s: %s", key, exc)
            self._miss()
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Write value to L1 + L2 (write-through style dual write)."""
        if not self._metrics_enabled():
            return False
        ok = False
        if self.use_l1:
            await self.l1.set(key, value, ttl)
            ok = True
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            payload = json.dumps(value, default=str, ensure_ascii=False)
            await r.setex(key, max(1, int(ttl)), payload)
            ok = True
            self._set()
        except Exception as exc:
            logger.debug("cache set failed key=%s: %s", key, exc)
        return ok

    async def delete(self, key: str) -> None:
        if self.use_l1:
            await self.l1.delete(key)
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            await r.delete(key)
            self._invalidate(1)
        except Exception as exc:
            logger.debug("cache delete failed key=%s: %s", key, exc)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a Redis glob pattern (and L1 prefix approx)."""
        count = 0
        # L1: treat pattern "af:task:list:*" as prefix before first *
        prefix = pattern.split("*", 1)[0]
        if self.use_l1 and prefix:
            count += await self.l1.delete_prefix(prefix)
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            # SCAN is safer than KEYS in production
            cursor = 0
            keys: list[str] = []
            while True:
                cursor, batch = await r.scan(cursor=cursor, match=pattern, count=200)
                keys.extend(batch)
                if cursor == 0:
                    break
            if keys:
                # delete in chunks
                for i in range(0, len(keys), 500):
                    chunk = keys[i : i + 500]
                    await r.delete(*chunk)
                count += len(keys)
                self._invalidate(len(keys))
        except Exception as exc:
            logger.debug("cache delete_pattern failed pattern=%s: %s", pattern, exc)
        return count

    async def get_or_set(
        self,
        key: str,
        factory,
        *,
        ttl: int = 300,
    ) -> Any:
        """Cache-aside: return cached value or compute, store, and return."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        if asyncio.iscoroutine(value):
            value = await value
        await self.set(key, value, ttl=ttl)
        return value

    async def incr(self, key: str, *, amount: int = 1, ttl: int | None = None) -> int:
        """Increment an integer counter in Redis (list version stamps)."""
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            val = await r.incrby(key, amount)
            if ttl is not None:
                await r.expire(key, max(1, int(ttl)))
            if self.use_l1:
                await self.l1.set(key, val, ttl or 86400)
            return int(val)
        except Exception:
            # Fallback: local version bump stored as string int
            cur = await self.l1.get(key)
            try:
                n = int(cur or 0) + amount
            except (TypeError, ValueError):
                n = amount
            await self.l1.set(key, n, ttl or 86400)
            return n

    def _hit(self, layer: str) -> None:
        try:
            from app.core.observability.metrics import observe_cache_hit

            observe_cache_hit(layer)
        except Exception:
            pass

    def _miss(self) -> None:
        try:
            from app.core.observability.metrics import observe_cache_miss

            observe_cache_miss()
        except Exception:
            pass

    def _set(self) -> None:
        try:
            from app.core.observability.metrics import observe_cache_set

            observe_cache_set()
        except Exception:
            pass

    def _invalidate(self, n: int) -> None:
        try:
            from app.core.observability.metrics import observe_cache_invalidate

            observe_cache_invalidate(n)
        except Exception:
            pass


_cache: CacheClient | None = None


def get_cache() -> CacheClient:
    """Process-wide cache client singleton."""
    global _cache
    if _cache is None:
        enabled = True
        try:
            from app.config import settings

            enabled = bool(getattr(settings, "CACHE_ENABLED", True))
        except Exception:
            pass
        _cache = CacheClient(enabled=enabled)
    return _cache


def reset_cache_client() -> None:
    """Reset singleton (tests)."""
    global _cache
    _cache = None
