# (c) 2026 AgentFlow-Eval
"""Tests for rate limiting.

E15f: /health calls ``_probe_services`` → module-level ``dependencies.engine``
(default agentflow_eval.db). Mock the probe and disable AOLS DB sink so this
rate-limit smoke test keeps composite /health coverage without opening the
default DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

_FAKE_SERVICES = {"database": "ok", "redis": "skipped (lite/eager)"}


@pytest.fixture(autouse=True)
def _isolate_health_probe():
    """Mock service probe + disable AOLS sink (E15f / E15c pattern)."""
    from app.core.observability.aols.sinks import db as aols_db_sink

    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))
    settings.LOG_DB_SINK = False
    probe = AsyncMock(return_value=dict(_FAKE_SERVICES))
    try:
        with patch("app.main._probe_services", probe):
            yield
    finally:
        try:
            with aols_db_sink._lock:
                aols_db_sink._queue.clear()
        except Exception:
            pass
        settings.LOG_DB_SINK = prev_sink


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
        assert data["status"] in ("healthy", "degraded")
