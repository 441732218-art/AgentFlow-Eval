# (c) 2026 AgentFlow-Eval
"""Tests for Redis cache helpers (compat layer → multi-level CacheClient)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache.client import reset_cache_client


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_cache_client()
    yield
    reset_cache_client()


class TestCache:
    """Test suite for cache_get/cache_set/cache_invalidate."""

    @pytest.fixture
    def mock_redis(self):
        """Mock redis client via get_redis dependency."""
        with patch("app.core.dependencies.get_redis") as mock_fn:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.setex = AsyncMock()
            mock_client.ttl = AsyncMock(return_value=60)
            mock_client.scan = AsyncMock(return_value=(0, ["test:1", "test:2"]))
            mock_client.delete = AsyncMock()
            mock_client.incrby = AsyncMock(return_value=1)
            mock_client.expire = AsyncMock()
            mock_fn.return_value = mock_client
            yield mock_fn, mock_client

    @pytest.mark.asyncio
    async def test_cache_set_get(self, mock_redis):
        """Setting and getting should return correct value (L1 or L2)."""
        from app.core.dependencies import cache_get, cache_set

        _, client = mock_redis
        client.get.return_value = '{"key": "value"}'

        await cache_set("test:key", {"key": "value"})
        # L1 serves after set without calling redis.get
        result = await cache_get("test:key")
        assert result == {"key": "value"}
        client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss(self, mock_redis):
        """Non-existent key should return None."""
        from app.core.dependencies import cache_get

        _, client = mock_redis
        client.get.return_value = None

        result = await cache_get("test:nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidate(self, mock_redis):
        """Invalidate should SCAN+delete matched keys."""
        from app.core.dependencies import cache_invalidate

        _, client = mock_redis
        client.scan = AsyncMock(return_value=(0, ["test:1", "test:2"]))

        await cache_invalidate("test:*")

        client.scan.assert_called()
        client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_unavailable(self):
        """When Redis is down, cache ops should not crash."""
        from app.core.dependencies import cache_get, cache_set

        with patch(
            "app.core.dependencies.get_redis",
            side_effect=ConnectionError("Redis down"),
        ):
            # First get — miss
            result = await cache_get("test:key")
            # May be None or L1 from prior tests; force new key
            result = await cache_get("test:never-set-xyz")
            assert result is None
            await cache_set("test:key2", "value")  # L1 write ok
