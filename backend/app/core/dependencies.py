# (c) 2026 AgentFlow-Eval
"""Dependency injection with database pool and Redis cache."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ---- Database engine with connection pool ----
_engine_kw: dict = {
    "echo": settings.DB_ECHO,
    "future": True,
}
if "postgresql" in settings.DATABASE_URL:
    _engine_kw.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })
engine = create_async_engine(settings.DATABASE_URL, **_engine_kw)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """Provide an async database session with auto-commit/rollback."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---- Redis cache ----
_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Lazy-init Redis connection pool."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            # Fail fast when Redis is down (local eager mode / offline)
            socket_timeout=0.8,
            socket_connect_timeout=0.5,
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection pool gracefully."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


# ---- Cache helpers ----
CACHE_TTL_DEFAULT = 300  # 5 minutes
CACHE_TTL_LIST = 60       # 1 minute for lists


async def cache_get(key: str) -> Any | None:
    """Get value from Redis cache."""
    try:
        r = await get_redis()
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_DEFAULT) -> None:
    """Set value in Redis cache with TTL."""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


async def cache_invalidate(pattern: str) -> None:
    """Invalidate all keys matching a pattern."""
    try:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
