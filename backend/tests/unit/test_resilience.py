# (c) 2026 AgentFlow-Eval
"""Unit tests for retry, circuit breaker, timeout, and fallback."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.core.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    ResiliencePolicy,
    TimeoutExceededError,
    default_llm_policy,
    protected_call,
    protected_call_async,
    reset_all_breakers,
    retry_async,
    retry_sync,
    with_timeout,
)
from app.core.resilience.circuit_breaker import get_breaker


@pytest.fixture(autouse=True)
def _reset_breakers():
    reset_all_breakers()
    yield
    reset_all_breakers()


class TestRetry:
    @pytest.mark.asyncio
    async def test_async_retry_succeeds_after_failures(self) -> None:
        calls = {"n": 0}

        async def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("transient")
            return "ok"

        with patch("app.core.resilience.retry._load_retry_settings", return_value=(3, 0.01, 0.05)):
            result = await retry_async(flaky, name="test", max_attempts=3, min_wait=0.01, max_wait=0.05)
        assert result == "ok"
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_async_retry_exhausted(self) -> None:
        async def always_fail() -> None:
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await retry_async(
                always_fail,
                name="test",
                max_attempts=3,
                min_wait=0.01,
                max_wait=0.02,
            )

    def test_sync_retry(self) -> None:
        calls = {"n": 0}

        def flaky() -> int:
            calls["n"] += 1
            if calls["n"] < 2:
                raise OSError("x")
            return 42

        assert retry_sync(flaky, name="t", max_attempts=3, min_wait=0.01, max_wait=0.02) == 42
        assert calls["n"] == 2


class TestCircuitBreaker:
    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker("t1", failure_threshold=5, recovery_timeout=60.0)

        def boom() -> None:
            raise ConnectionError("fail")

        for _ in range(5):
            with pytest.raises(ConnectionError):
                cb.call(boom)
        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitOpenError):
            cb.call(lambda: "nope")

    def test_half_open_then_close(self) -> None:
        cb = CircuitBreaker("t2", failure_threshold=2, recovery_timeout=0.05)

        def boom() -> None:
            raise ConnectionError("fail")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                cb.call(boom)
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.call(lambda: "ok") == "ok"
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker("t3", failure_threshold=1, recovery_timeout=0.05)

        with pytest.raises(ConnectionError):
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("x")))
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)

        def boom() -> None:
            raise ConnectionError("again")

        with pytest.raises(ConnectionError):
            cb.call(boom)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_async_call(self) -> None:
        cb = CircuitBreaker("t4", failure_threshold=5, recovery_timeout=60)

        async def ok() -> str:
            return "yes"

        assert await cb.call_async(ok) == "yes"

    def test_get_breaker_singleton(self) -> None:
        a = get_breaker("shared", failure_threshold=5, recovery_timeout=60)
        b = get_breaker("shared")
        assert a is b


class TestTimeout:
    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        async def slow() -> None:
            await asyncio.sleep(1.0)

        with pytest.raises(TimeoutExceededError):
            await with_timeout(slow(), timeout_sec=0.05, name="slow")

    @pytest.mark.asyncio
    async def test_timeout_ok(self) -> None:
        async def fast() -> str:
            return "fast"

        assert await with_timeout(fast(), timeout_sec=1.0, name="fast") == "fast"


class TestProtectedCall:
    @pytest.mark.asyncio
    async def test_fallback_on_failure(self) -> None:
        async def fail() -> str:
            raise ConnectionError("nope")

        async def fb() -> str:
            return "rule"

        policy = ResiliencePolicy(
            name="fb_test",
            max_attempts=2,
            min_wait=0.01,
            max_wait=0.02,
            timeout_sec=1.0,
            failure_threshold=10,
            recovery_timeout=60.0,
        )
        result = await protected_call_async(fail, policy=policy, fallback=fb)
        assert result == "rule"

    @pytest.mark.asyncio
    async def test_fallback_on_circuit_open(self) -> None:
        policy = ResiliencePolicy(
            name="open_test",
            max_attempts=1,
            min_wait=0.01,
            max_wait=0.01,
            timeout_sec=1.0,
            failure_threshold=2,
            recovery_timeout=60.0,
        )

        async def fail() -> str:
            raise ConnectionError("x")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await protected_call_async(fail, policy=policy)

        result = await protected_call_async(
            fail, policy=policy, fallback=lambda: "degraded"
        )
        assert result == "degraded"

    @pytest.mark.asyncio
    async def test_success_path(self) -> None:
        policy = ResiliencePolicy(
            name="ok_test",
            max_attempts=2,
            min_wait=0.01,
            max_wait=0.01,
            timeout_sec=2.0,
            failure_threshold=5,
            recovery_timeout=60.0,
        )

        async def ok() -> int:
            return 7

        assert await protected_call_async(ok, policy=policy) == 7

    def test_sync_protected_call_fallback(self) -> None:
        policy = ResiliencePolicy(
            name="sync_fb",
            max_attempts=2,
            min_wait=0.01,
            max_wait=0.01,
            timeout_sec=1.0,
            failure_threshold=10,
            recovery_timeout=60.0,
        )

        def fail() -> str:
            raise ConnectionError("x")

        assert protected_call(fail, policy=policy, fallback=lambda: "fb") == "fb"

    def test_default_llm_policy_reads_settings(self) -> None:
        p = default_llm_policy("llm")
        assert p.max_attempts >= 1
        assert p.timeout_sec > 0
        assert p.failure_threshold >= 1


class TestJudgeDegradation:
    @pytest.mark.asyncio
    async def test_llm_refine_falls_back_to_rules(self) -> None:
        from app.core.judge_engine.llm_judge import LLMJudge
        from app.core.resilience import reset_all_breakers

        reset_all_breakers()
        judge = LLMJudge(api_key="fake", timeout_sec=0, cache_size=0)
        judge.has_api_key = True

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=ConnectionError("llm down")
        )
        judge.client = client

        # Speed up retries
        fast = ResiliencePolicy(
            name="llm_judge:gpt-4o-mini",
            max_attempts=2,
            min_wait=0.01,
            max_wait=0.02,
            timeout_sec=1.0,
            failure_threshold=50,
            recovery_timeout=60.0,
        )
        with patch(
            "app.core.judge_engine.llm_judge.default_llm_policy",
            return_value=fast,
        ):
            result = await judge.evaluate(
                [{"action": "final_answer", "action_input": "hello world"}],
                "hello world",
                [],
            )
        assert result["mode"] == "rule_only"
        assert result.get("degraded") is True
        assert "scores" in result
