# (c) 2026 AgentFlow-Eval
"""Tests for rate limiting."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


class TestRateLimit:
    """Test suite for rate limiting middleware."""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_normal_request(self, client):
        """Health check should return 200 without rate limits."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
