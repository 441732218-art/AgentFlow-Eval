# (c) 2026 AgentFlow-Eval
"""Timeout wrappers for sync and async callables."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TimeoutExceededError(TimeoutError):
    """Raised when an operation exceeds its configured timeout."""

    def __init__(self, name: str, timeout_sec: float) -> None:
        self.name = name
        self.timeout_sec = timeout_sec
        super().__init__(f"'{name}' timed out after {timeout_sec}s")


def _default_timeout() -> float:
    try:
        from app.config import settings

        return float(getattr(settings, "LLM_CALL_TIMEOUT_SEC", 30.0) or 30.0)
    except Exception:
        return 30.0


def _record_timeout(name: str) -> None:
    try:
        from app.core.observability.metrics import observe_timeout

        observe_timeout(name)
    except Exception:
        pass


async def with_timeout(
    awaitable: Awaitable[T],
    *,
    timeout_sec: float | None = None,
    name: str = "operation",
) -> T:
    """Await ``awaitable`` with a deadline (default 30s from settings)."""
    limit = timeout_sec if timeout_sec is not None else _default_timeout()
    if limit <= 0:
        return await awaitable
    try:
        return await asyncio.wait_for(awaitable, timeout=limit)
    except asyncio.TimeoutError as exc:
        _record_timeout(name)
        logger.warning("Timeout: %s after %.1fs", name, limit)
        raise TimeoutExceededError(name, limit) from exc


def with_timeout_sync(
    fn: Callable[..., T],
    *args: Any,
    timeout_sec: float | None = None,
    name: str = "operation",
    **kwargs: Any,
) -> T:
    """Run a sync callable in a worker thread with a deadline."""
    limit = timeout_sec if timeout_sec is not None else _default_timeout()
    if limit <= 0:
        return fn(*args, **kwargs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=limit)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            _record_timeout(name)
            logger.warning("Timeout: %s after %.1fs", name, limit)
            raise TimeoutExceededError(name, limit) from exc
