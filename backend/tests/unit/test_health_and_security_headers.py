# (c) 2026 AgentFlow-Eval
"""Tests for health probes and security response headers.

E15c: /health and /health/ready call ``_probe_services`` which opens the
module-level ``dependencies.engine`` (default agentflow_eval.db). These tests
assert HTTP semantics only, so the probe is mocked and AOLS DB sink is
disabled — no default DB connection and no get_db override needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

# Controlled probe payload: DB ok, redis skipped → ready/healthy HTTP paths.
_FAKE_SERVICES = {"database": "ok", "redis": "skipped (lite/eager)"}


@pytest.fixture(autouse=True)
def _isolate_health_defaults():
    """Mock service probe + disable AOLS sink (E15c). Restores settings only."""
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


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthProbes:
    @pytest.mark.asyncio
    async def test_liveness(self, client) -> None:
        # /health/live does not call _probe_services or the DB engine.
        async with client as c:
            r = await c.get("/health/live")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "alive"
        assert "version" in body

    @pytest.mark.asyncio
    async def test_readiness_ok(self, client) -> None:
        async with client as c:
            r = await c.get("/health/ready")
        # With isolated probe returning database=ok → ready (200).
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert "services" in body
        assert body["services"]["database"] == "ok"

    @pytest.mark.asyncio
    async def test_composite_health(self, client) -> None:
        async with client as c:
            r = await c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert "services" in body
        assert body["services"]["database"] == "ok"

    @pytest.mark.asyncio
    async def test_health_public_with_auth(self, client) -> None:
        with patch("app.core.middleware.settings") as s:
            s.AUTH_ENABLED = True
            async with client as c:
                live = await c.get("/health/live")
                ready = await c.get("/health/ready")
                health = await c.get("/health")
        assert live.status_code == 200
        assert ready.status_code == 200
        assert health.status_code == 200


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client) -> None:
        async with client as c:
            r = await c.get("/health/live")
        assert r.status_code == 200
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in r.headers
        assert r.headers.get("X-Request-ID")  # RequestID middleware

    @pytest.mark.asyncio
    async def test_hsts_only_in_prod(self, client) -> None:
        with patch("app.core.middleware.settings") as s:
            s.is_prod = True
            s.DEBUG = False
            async with client as c:
                r = await c.get("/health/live")
        assert "Strict-Transport-Security" in r.headers
