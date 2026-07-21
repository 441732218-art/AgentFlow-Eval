# (c) 2026 AgentFlow-Eval
"""Composed resilience policy: circuit + retry + timeout + fallback."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from app.core.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    get_breaker,
)
from app.core.resilience.retry import DEFAULT_RETRY_EXCEPTIONS, retry_async, retry_sync
from app.core.resilience.timeout import (
    TimeoutExceededError,
    with_timeout,
    with_timeout_sync,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class ResiliencePolicy:
    """Configuration bundle for protected external calls."""

    name: str = "llm"
    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 10.0
    timeout_sec: float = 30.0
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    retry_exceptions: tuple[type[BaseException], ...] = DEFAULT_RETRY_EXCEPTIONS
    enable_circuit: bool = True
    enable_retry: bool = True


def default_llm_policy(name: str = "llm") -> ResiliencePolicy:
    """Build policy from application settings."""
    try:
        from app.config import settings

        return ResiliencePolicy(
            name=name,
            max_attempts=int(getattr(settings, "LLM_MAX_RETRIES", 3) or 3),
            min_wait=float(getattr(settings, "LLM_RETRY_MIN_WAIT_SEC", 1.0) or 1.0),
            max_wait=float(getattr(settings, "LLM_RETRY_MAX_WAIT_SEC", 10.0) or 10.0),
            timeout_sec=float(getattr(settings, "LLM_CALL_TIMEOUT_SEC", 30.0) or 30.0),
            failure_threshold=int(
                getattr(settings, "CIRCUIT_FAILURE_THRESHOLD", 5) or 5
            ),
            recovery_timeout=float(
                getattr(settings, "CIRCUIT_RECOVERY_TIMEOUT_SEC", 60.0) or 60.0
            ),
            enable_circuit=bool(getattr(settings, "CIRCUIT_ENABLED", True)),
            enable_retry=bool(getattr(settings, "LLM_RETRY_ENABLED", True)),
        )
    except Exception:
        return ResiliencePolicy(name=name)


def _record_fallback(name: str, reason: str) -> None:
    try:
        from app.core.observability.metrics import observe_fallback

        observe_fallback(name, reason)
    except Exception:
        pass


async def protected_call_async(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    policy: ResiliencePolicy | None = None,
    fallback: Callable[..., Awaitable[T] | T] | None = None,
    **kwargs: Any,
) -> T:
    """Execute an async call with circuit breaker, retry, timeout, and optional fallback.

    Flow:
      1. Circuit open? → fallback or raise CircuitOpenError
      2. Each attempt wrapped in timeout
      3. Transient failures retried (tenacity exponential backoff, max 3)
      4. Success / failure recorded on circuit breaker
      5. Exhausted / open → invoke fallback if provided

    Args:
        fn: Async callable.
        policy: Resilience knobs; defaults to LLM settings.
        fallback: Sync or async callable used on terminal failure.
    """
    pol = policy or default_llm_policy()
    breaker: CircuitBreaker | None = None
    if pol.enable_circuit:
        breaker = get_breaker(
            pol.name,
            failure_threshold=pol.failure_threshold,
            recovery_timeout=pol.recovery_timeout,
        )

    async def _one_attempt() -> T:
        return await with_timeout(
            fn(*args, **kwargs),
            timeout_sec=pol.timeout_sec,
            name=pol.name,
        )

    async def _run() -> T:
        if pol.enable_retry:
            return await retry_async(
                _one_attempt,
                name=pol.name,
                max_attempts=pol.max_attempts,
                min_wait=pol.min_wait,
                max_wait=pol.max_wait,
                retry_exceptions=pol.retry_exceptions + (TimeoutExceededError,),
            )
        return await _one_attempt()

    try:
        if breaker is not None:
            return await breaker.call_async(_run)
        return await _run()
    except CircuitOpenError as exc:
        logger.warning("Protected call '%s' short-circuited: %s", pol.name, exc)
        if fallback is not None:
            _record_fallback(pol.name, "circuit_open")
            return await _invoke_fallback_async(fallback, *args, **kwargs)
        raise
    except Exception as exc:
        logger.warning("Protected call '%s' failed: %s", pol.name, exc)
        if fallback is not None:
            reason = (
                "timeout"
                if isinstance(exc, (TimeoutError, TimeoutExceededError))
                else "error"
            )
            _record_fallback(pol.name, reason)
            return await _invoke_fallback_async(fallback, *args, **kwargs)
        raise


def protected_call(
    fn: Callable[..., T],
    *args: Any,
    policy: ResiliencePolicy | None = None,
    fallback: Callable[..., T] | None = None,
    **kwargs: Any,
) -> T:
    """Sync variant of :func:`protected_call_async`."""
    pol = policy or default_llm_policy()
    breaker: CircuitBreaker | None = None
    if pol.enable_circuit:
        breaker = get_breaker(
            pol.name,
            failure_threshold=pol.failure_threshold,
            recovery_timeout=pol.recovery_timeout,
        )

    def _one_attempt() -> T:
        return with_timeout_sync(
            fn,
            *args,
            timeout_sec=pol.timeout_sec,
            name=pol.name,
            **kwargs,
        )

    def _run() -> T:
        if pol.enable_retry:
            return retry_sync(
                _one_attempt,
                name=pol.name,
                max_attempts=pol.max_attempts,
                min_wait=pol.min_wait,
                max_wait=pol.max_wait,
                retry_exceptions=pol.retry_exceptions + (TimeoutExceededError,),
            )
        return _one_attempt()

    try:
        if breaker is not None:
            return breaker.call(_run)
        return _run()
    except CircuitOpenError as exc:
        logger.warning("Protected call '%s' short-circuited: %s", pol.name, exc)
        if fallback is not None:
            _record_fallback(pol.name, "circuit_open")
            return fallback(*args, **kwargs)
        raise
    except Exception as exc:
        logger.warning("Protected call '%s' failed: %s", pol.name, exc)
        if fallback is not None:
            reason = (
                "timeout"
                if isinstance(exc, (TimeoutError, TimeoutExceededError))
                else "error"
            )
            _record_fallback(pol.name, reason)
            return fallback(*args, **kwargs)
        raise


async def _invoke_fallback_async(
    fallback: Callable[..., Awaitable[T] | T],
    *args: Any,
    **kwargs: Any,
) -> T:
    import inspect

    result = fallback(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result  # type: ignore[misc]
    return result  # type: ignore[return-value]
