# (c) 2026 AgentFlow-Eval
"""Async-safe circuit breaker (closed → open → half-open).

Semantics (aligned with common circuitbreaker / pybreaker defaults):
  - failure_threshold: consecutive failures before opening (default 5)
  - recovery_timeout: seconds in OPEN before allowing a probe (default 60)
  - half-open: one successful probe closes the circuit; any failure re-opens
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str, recovery_remaining: float = 0.0) -> None:
        self.name = name
        self.recovery_remaining = recovery_remaining
        super().__init__(
            f"Circuit '{name}' is OPEN (retry in ~{recovery_remaining:.1f}s)"
        )


class CircuitBreaker:
    """Thread-safe circuit breaker for sync and async callables."""

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 1,
        excluded_exceptions: tuple[type[BaseException], ...] = (),
    ) -> None:
        """Initialize a named circuit breaker.

        Args:
            name: Breaker identity (used in logs/metrics).
            failure_threshold: Consecutive failures to open the circuit.
            recovery_timeout: Seconds to wait before half-open probe.
            success_threshold: Successes in half-open required to close.
            excluded_exceptions: Exceptions that do not count as failures.
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")

        self.name = name
        self.failure_threshold = int(failure_threshold)
        self.recovery_timeout = float(recovery_timeout)
        self.success_threshold = max(1, int(success_threshold))
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at: float | None = None
        self._lock = threading.RLock()

    # ---- state introspection ----

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def reset(self) -> None:
        """Force circuit back to CLOSED (tests / admin)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None
        self._emit_state()

    def _maybe_transition_to_half_open(self) -> None:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return
        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self.recovery_timeout:
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            logger.info("Circuit '%s' → HALF_OPEN (probe allowed)", self.name)
            self._emit_state_unlocked()

    def _recovery_remaining(self) -> float:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return 0.0
        left = self.recovery_timeout - (time.monotonic() - self._opened_at)
        return max(0.0, left)

    def _before_call(self) -> None:
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state == CircuitState.OPEN:
                raise CircuitOpenError(self.name, self._recovery_remaining())

    def _on_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._opened_at = None
                    logger.info("Circuit '%s' → CLOSED (probe succeeded)", self.name)
                    self._emit_state_unlocked()
            else:
                self._failure_count = 0
        self._record_result("success")

    def _on_failure(self, exc: BaseException) -> None:
        if isinstance(exc, self.excluded_exceptions):
            return
        with self._lock:
            self._failure_count += 1
            if self._state == CircuitState.HALF_OPEN:
                self._trip_open()
            elif (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self.failure_threshold
            ):
                self._trip_open()
        self._record_result("failure")

    def _trip_open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._success_count = 0
        logger.warning(
            "Circuit '%s' → OPEN after %d failures (recovery=%.0fs)",
            self.name,
            self._failure_count,
            self.recovery_timeout,
        )
        self._emit_state_unlocked()

    def _emit_state(self) -> None:
        with self._lock:
            self._emit_state_unlocked()

    def _emit_state_unlocked(self) -> None:
        try:
            from app.core.observability.metrics import observe_circuit_state

            observe_circuit_state(self.name, self._state.value)
        except Exception:
            pass

    def _record_result(self, result: str) -> None:
        try:
            from app.core.observability.metrics import observe_circuit_call

            observe_circuit_call(self.name, result)
        except Exception:
            pass

    # ---- execution ----

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a sync callable through the breaker."""
        self._before_call()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._on_failure(exc)
            raise
        self._on_success()
        return result

    async def call_async(
        self,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute an async callable through the breaker."""
        self._before_call()
        try:
            result = await fn(*args, **kwargs)
        except Exception as exc:
            self._on_failure(exc)
            raise
        self._on_success()
        return result

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator for sync or async functions."""
        import functools
        import inspect

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.call_async(fn, *args, **kwargs)

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(fn, *args, **kwargs)

        return sync_wrapper


# Process-wide named breakers
_BREAKERS: dict[str, CircuitBreaker] = {}
_BREAKERS_LOCK = threading.Lock()


def get_breaker(
    name: str,
    *,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
) -> CircuitBreaker:
    """Get or create a process-wide named circuit breaker.

    Thresholds are read from settings when not provided.
    """
    with _BREAKERS_LOCK:
        if name in _BREAKERS:
            return _BREAKERS[name]
        ft, rt = failure_threshold, recovery_timeout
        if ft is None or rt is None:
            try:
                from app.config import settings

                if ft is None:
                    ft = int(getattr(settings, "CIRCUIT_FAILURE_THRESHOLD", 5))
                if rt is None:
                    rt = float(getattr(settings, "CIRCUIT_RECOVERY_TIMEOUT_SEC", 60.0))
            except Exception:
                ft = ft if ft is not None else 5
                rt = rt if rt is not None else 60.0
        breaker = CircuitBreaker(
            name,
            failure_threshold=ft,
            recovery_timeout=rt,
        )
        _BREAKERS[name] = breaker
        return breaker


def reset_all_breakers() -> None:
    """Reset all registered breakers (tests)."""
    with _BREAKERS_LOCK:
        for b in _BREAKERS.values():
            b.reset()
        _BREAKERS.clear()
