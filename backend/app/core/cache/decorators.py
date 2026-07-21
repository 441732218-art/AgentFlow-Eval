# (c) 2026 AgentFlow-Eval
"""Caching decorators: cache-aside and write-through."""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from app.core.cache.client import get_cache
from app.core.cache.keys import CacheTTL, cache_key

P = ParamSpec("P")
R = TypeVar("R")


def _default_key(
    fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    """Stable key from function name + JSON args (skip Request/session-like objs)."""
    skip_types = set()
    try:
        from fastapi import Request
        from sqlalchemy.ext.asyncio import AsyncSession

        skip_types = {Request, AsyncSession}
    except Exception:
        pass

    serializable: list[Any] = []
    for a in args:
        if type(a) in skip_types or a.__class__.__name__ in {
            "Request",
            "AsyncSession",
        }:
            continue
        try:
            json.dumps(a, default=str)
            serializable.append(a)
        except Exception:
            serializable.append(repr(a))
    for k, v in sorted(kwargs.items()):
        if k in {"request", "session", "db"}:
            continue
        if type(v) in skip_types:
            continue
        serializable.append({k: v})
    raw = json.dumps(serializable, default=str, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return cache_key("fn", fn.__module__, fn.__qualname__, digest)


def cached(
    *,
    ttl: int = CacheTTL.DEFAULT,
    key_builder: Callable[..., str] | None = None,
    namespace: str | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Cache-aside decorator for async callables.

    On hit returns cached JSON-compatible value; on miss calls function and stores result.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("@cached only supports async functions")

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cache = get_cache()
            if key_builder is not None:
                key = key_builder(*args, **kwargs)
            else:
                key = _default_key(fn, args, kwargs)
            if namespace:
                key = cache_key(namespace, key)
            hit = await cache.get(key)
            if hit is not None:
                return hit  # type: ignore[return-value]
            result = await fn(*args, **kwargs)
            # Only cache JSON-serializable payloads (dict/list/primitives)
            try:
                json.dumps(result, default=str)
                await cache.set(key, result, ttl=int(ttl))
            except Exception:
                pass
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def cached_write_through(
    *,
    ttl: int = CacheTTL.DEFAULT,
    key_builder: Callable[..., str],
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Write-through: always execute function, then update cache with result.

    Useful for mutations that return the new representation to clients.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("@cached_write_through only supports async functions")

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = await fn(*args, **kwargs)
            try:
                key = key_builder(*args, **kwargs)
                json.dumps(result, default=str)
                await get_cache().set(key, result, ttl=int(ttl))
            except Exception:
                pass
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
