# (c) 2026 AgentFlow-Eval
"""Tests for Redis cache helpers."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestCache:
    """Test suite for cache_get/cache_set/cache_invalidate."""

    @pytest.fixture
    def mock_redis(self):
        """Mock redis client via get_redis dependency."""
        with patch("app.core.dependencies.get_redis") as mock_fn:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.setex = AsyncMock()
            mock_client.keys = AsyncMock()
            mock_client.delete = AsyncMock()
            mock_fn.return_value = mock_client
            yield mock_fn, mock_client

    @pytest.mark.asyncio
    async def test_cache_set_get(self, mock_redis):
        """Setting and getting should return correct value."""
        from app.core.dependencies import cache_set, cache_get
        _, client = mock_redis

        client.get.return_value = '{"key": "value"}'

        await cache_set("test:key", {"key": "value"})
        result = await cache_get("test:key")

        assert result == {"key": "value"}
        client.setex.assert_called_once()
        client.get.assert_called_once_with("test:key")

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
        """Invalidate should delete matched keys."""
        from app.core.dependencies import cache_invalidate
        _, client = mock_redis

        client.keys.return_value = ["test:1", "test:2"]

        await cache_invalidate("test:*")

        client.keys.assert_called_once_with("test:*")
        client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_unavailable(self):
        """When Redis is down, cache ops should return None gracefully."""
        from app.core.dependencies import cache_get, cache_set
        with patch("app.core.dependencies.get_redis", side_effect=ConnectionError("Redis down")):
            result = await cache_get("test:key")
            assert result is None

            # set should not raise
            await cache_set("test:key", "value")  # no assertion needed, just should not crash
