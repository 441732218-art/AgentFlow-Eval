# (c) 2026 AgentFlow-Eval
"""Retry helpers built on tenacity (exponential backoff)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryCallState,
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

def _collect_retry_exceptions() -> tuple[type[BaseException], ...]:
    """Build the default set of transient exception types to retry."""
    import asyncio

    errs: list[type[BaseException]] = [TimeoutError, ConnectionError, OSError]
    # On 3.11+ asyncio.TimeoutError is TimeoutError; keep both for safety
    if asyncio.TimeoutError is not TimeoutError:  # type: ignore[comparison-overlap]
        errs.append(asyncio.TimeoutError)
    try:
        import httpx

        errs.extend((httpx.TimeoutException, httpx.TransportError))
    except ImportError:
        pass
    try:
        import openai

        for name in ("APITimeoutError", "APIConnectionError", "RateLimitError"):
            cls = getattr(openai, name, None)
            if isinstance(cls, type) and issubclass(cls, BaseException):
                errs.append(cls)
    except ImportError:
        pass
    # Deduplicate while preserving order
    seen: set[type[BaseException]] = set()
    unique: list[type[BaseException]] = []
    for e in errs:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return tuple(unique)


# Transient errors typical of LLM / HTTP clients
DEFAULT_RETRY_EXCEPTIONS: tuple[type[BaseException], ...] = _collect_retry_exceptions()


def _load_retry_settings() -> tuple[int, float, float]:
    try:
        from app.config import settings

        attempts = int(getattr(settings, "LLM_MAX_RETRIES", 3) or 3)
        min_wait = float(getattr(settings, "LLM_RETRY_MIN_WAIT_SEC", 1.0) or 1.0)
        max_wait = float(getattr(settings, "LLM_RETRY_MAX_WAIT_SEC", 10.0) or 10.0)
        return max(1, attempts), min_wait, max_wait
    except Exception:
        return 3, 1.0, 10.0


def _before_sleep(name: str) -> Callable[[RetryCallState], None]:
    def _cb(state: RetryCallState) -> None:
        exc = state.outcome.exception() if state.outcome else None
        logger.warning(
            "Retry %s attempt=%s next_wait=%.2fs error=%s",
            name,
            state.attempt_number,
            state.next_action.sleep if state.next_action else 0,
            exc,
        )
        try:
            from app.core.observability.metrics import observe_retry

            observe_retry(name, attempt=state.attempt_number)
        except Exception:
            pass

    return _cb


def async_retrying(
    *,
    name: str = "llm",
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
    retry_exceptions: tuple[type[BaseException], ...] | None = None,
) -> AsyncRetrying:
    """Build an ``AsyncRetrying`` controller with exponential backoff."""
    attempts, d_min, d_max = _load_retry_settings()
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts or attempts),
        wait=wait_exponential(
            multiplier=1,
            min=min_wait if min_wait is not None else d_min,
            max=max_wait if max_wait is not None else d_max,
        ),
        retry=retry_if_exception_type(retry_exceptions or DEFAULT_RETRY_EXCEPTIONS),
        before_sleep=_before_sleep(name),
        reraise=True,
    )


def sync_retrying(
    *,
    name: str = "llm",
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
    retry_exceptions: tuple[type[BaseException], ...] | None = None,
) -> Retrying:
    """Build a sync ``Retrying`` controller."""
    attempts, d_min, d_max = _load_retry_settings()
    return Retrying(
        stop=stop_after_attempt(max_attempts or attempts),
        wait=wait_exponential(
            multiplier=1,
            min=min_wait if min_wait is not None else d_min,
            max=max_wait if max_wait is not None else d_max,
        ),
        retry=retry_if_exception_type(retry_exceptions or DEFAULT_RETRY_EXCEPTIONS),
        before_sleep=_before_sleep(name),
        reraise=True,
    )


async def retry_async(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    name: str = "llm",
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
    retry_exceptions: tuple[type[BaseException], ...] | None = None,
    **kwargs: Any,
) -> T:
    """Run an async callable with tenacity exponential backoff retries."""
    controller = async_retrying(
        name=name,
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        retry_exceptions=retry_exceptions,
    )
    async for attempt in controller:
        with attempt:
            return await fn(*args, **kwargs)
    raise RuntimeError("retry_async exhausted without result")  # pragma: no cover


def retry_sync(
    fn: Callable[..., T],
    *args: Any,
    name: str = "llm",
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
    retry_exceptions: tuple[type[BaseException], ...] | None = None,
    **kwargs: Any,
) -> T:
    """Run a sync callable with tenacity exponential backoff retries."""
    controller = sync_retrying(
        name=name,
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        retry_exceptions=retry_exceptions,
    )
    for attempt in controller:
        with attempt:
            return fn(*args, **kwargs)
    raise RuntimeError("retry_sync exhausted without result")  # pragma: no cover


__all__ = [
    "DEFAULT_RETRY_EXCEPTIONS",
    "RetryError",
    "async_retrying",
    "retry_async",
    "retry_sync",
    "sync_retrying",
]
