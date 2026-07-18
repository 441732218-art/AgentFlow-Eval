# (c) 2026 AgentFlow-Eval
"""Tests for health probes and security response headers."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthProbes:
    @pytest.mark.asyncio
    async def test_liveness(self, client) -> None:
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
        # DB may or may not be configured; when ok expect 200, else 503
        assert r.status_code in (200, 503)
        body = r.json()
        assert body["status"] in ("ready", "not_ready")
        assert "services" in body

    @pytest.mark.asyncio
    async def test_composite_health(self, client) -> None:
        async with client as c:
            r = await c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("healthy", "degraded")
        assert "services" in body

    @pytest.mark.asyncio
    async def test_health_public_with_auth(self, client) -> None:
        with patch("app.core.middleware.settings") as s:
            s.AUTH_ENABLED = True
            async with client as c:
                live = await c.get("/health/live")
                ready = await c.get("/health/ready")
                health = await c.get("/health")
        assert live.status_code == 200
        assert ready.status_code in (200, 503)
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
