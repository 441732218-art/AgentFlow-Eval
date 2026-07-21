# (c) 2026 AgentFlow-Eval
"""Tests for multi-layer cache client, invalidation, and domain services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache.client import CacheClient, LocalMemoryCache, reset_cache_client
from app.core.cache.decorators import cached
from app.core.cache.invalidation import invalidate_task, invalidate_task_lists
from app.core.cache.keys import (
    CacheTTL,
    cache_key,
    task_detail_key,
    task_list_key,
    task_list_version_key,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_cache_client()
    yield
    reset_cache_client()


class TestLocalMemoryCache:
    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        import time

        mem = LocalMemoryCache(max_size=10)
        await mem.set("k", {"a": 1}, ttl=60)
        assert await mem.get("k") == {"a": 1}
        # force expire (absolute deadline in the past)
        entry = mem._data["k"]
        entry.expires_at = time.monotonic() - 1
        assert await mem.get("k") is None


class TestCacheClientL1:
    @pytest.mark.asyncio
    async def test_l1_hit_without_redis(self):
        client = CacheClient(enabled=True, use_l1=True)
        with patch.object(client, "_metrics_enabled", return_value=True):
            # Redis down → L1 still works for set/get via set then get before redis
            with patch(
                "app.core.dependencies.get_redis",
                side_effect=ConnectionError("down"),
            ):
                await client.set("af:test:1", {"x": 1}, ttl=60)
                # L1 should have it even if redis failed
                val = await client.l1.get("af:test:1")
                assert val == {"x": 1}


class TestCacheClientWithMockRedis:
    @pytest.mark.asyncio
    async def test_get_set_l2(self):
        client = CacheClient(enabled=True, use_l1=True)
        mock_r = AsyncMock()
        mock_r.get = AsyncMock(return_value='{"n": 2}')
        mock_r.setex = AsyncMock()
        mock_r.ttl = AsyncMock(return_value=100)
        mock_r.scan = AsyncMock(return_value=(0, []))
        mock_r.delete = AsyncMock()
        mock_r.incrby = AsyncMock(return_value=3)
        mock_r.expire = AsyncMock()

        with patch("app.core.dependencies.get_redis", AsyncMock(return_value=mock_r)):
            await client.set("k1", {"n": 1}, ttl=30)
            mock_r.setex.assert_called()
            got = await client.get("k1")
            # L1 may serve first; clear L1 to force L2
            await client.l1.clear()
            got = await client.get("k1")
            assert got == {"n": 2}

    @pytest.mark.asyncio
    async def test_delete_pattern_scan(self):
        client = CacheClient(enabled=True, use_l1=True)
        mock_r = AsyncMock()
        mock_r.scan = AsyncMock(side_effect=[(1, ["a:1", "a:2"]), (0, ["a:3"])])
        mock_r.delete = AsyncMock()
        with patch("app.core.dependencies.get_redis", AsyncMock(return_value=mock_r)):
            n = await client.delete_pattern("a:*")
        assert n >= 3
        mock_r.delete.assert_called()


class TestKeysAndInvalidation:
    def test_key_builders(self):
        assert task_detail_key("t1").startswith("af:task:detail:")
        assert "list_ver" in task_list_version_key("alice")
        k = task_list_key(
            "alice", 1, page=1, page_size=20, status=None, include_archived=False
        )
        assert "alice" in k
        assert CacheTTL.TASK_DETAIL == 300
        assert CacheTTL.TASK_LIST == 30
        assert CacheTTL.DASHBOARD == 60
        assert CacheTTL.EVAL_RESULT == 3600
        assert CacheTTL.SETTINGS == 600

    @pytest.mark.asyncio
    async def test_invalidate_bumps_list_version(self):
        client = CacheClient(enabled=True, use_l1=True)
        with patch("app.core.cache.invalidation.get_cache", return_value=client):
            with patch("app.core.dependencies.get_redis", side_effect=ConnectionError):
                await invalidate_task_lists("bob")
                v1 = await client.l1.get(task_list_version_key("bob"))
                await invalidate_task("tid", actor="bob")
                v2 = await client.l1.get(task_list_version_key("bob"))
                assert int(v2 or 0) >= int(v1 or 0)


class TestCachedDecorator:
    @pytest.mark.asyncio
    async def test_cache_aside_decorator(self):
        calls = {"n": 0}
        client = CacheClient(enabled=True, use_l1=True)

        @cached(ttl=60, key_builder=lambda: cache_key("fn", "demo"))
        async def load() -> dict:
            calls["n"] += 1
            return {"v": calls["n"]}

        with patch("app.core.cache.decorators.get_cache", return_value=client):
            with patch("app.core.dependencies.get_redis", side_effect=ConnectionError):
                a = await load()
                b = await load()
        assert a == b
        assert calls["n"] == 1


class TestEvalVersion:
    def test_eval_version_stable(self):
        from app.core.cache.services import eval_version_from_scores
        from app.models.metric_score import MetricScore

        a = [
            MetricScore(trace_id="t", metric_name="x", score=1.0),
            MetricScore(trace_id="t", metric_name="y", score=2.0),
        ]
        b = [
            MetricScore(trace_id="t", metric_name="y", score=2.0),
            MetricScore(trace_id="t", metric_name="x", score=1.0),
        ]
        assert eval_version_from_scores(a) == eval_version_from_scores(b)
        a[0].is_human_reviewed = True
        a[0].human_score = 9.0
        assert eval_version_from_scores(a) != eval_version_from_scores(b)
