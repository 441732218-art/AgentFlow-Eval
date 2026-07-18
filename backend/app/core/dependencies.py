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
_db_url = settings.DATABASE_URL or ""
if "postgresql" in _db_url:
    _engine_kw.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })
elif "sqlite" in _db_url:
    # SQLite: avoid cross-thread issues; enable WAL via connect event below
    _engine_kw.update({
        "connect_args": {"check_same_thread": False},
    })

engine = create_async_engine(settings.DATABASE_URL, **_engine_kw)


# SQLite performance pragmas (WAL + reasonable sync for local/dev)
if "sqlite" in _db_url:
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_on_connect(dbapi_conn, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

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


# ---- Cache helpers (compat wrappers → app.core.cache) ----
CACHE_TTL_DEFAULT = 300  # 5 minutes
CACHE_TTL_LIST = 60  # 1 minute for lists


async def cache_get(key: str) -> Any | None:
    """Get value from multi-layer cache (L1 + Redis)."""
    from app.core.cache.client import get_cache

    return await get_cache().get(key)


async def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_DEFAULT) -> None:
    """Set value in multi-layer cache with TTL."""
    from app.core.cache.client import get_cache

    await get_cache().set(key, value, ttl=ttl)


async def cache_invalidate(pattern: str) -> None:
    """Invalidate all keys matching a pattern."""
    from app.core.cache.client import get_cache

    await get_cache().delete_pattern(pattern)
