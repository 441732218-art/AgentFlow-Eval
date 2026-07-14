# (c) 2026 AgentFlow-Eval
"""Tests for API key auth helpers and middleware behavior."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from app.core.security import authenticate_api_key, parse_api_keys
from app.main import app


class TestSecurityHelpers:
    def test_parse_plain_keys(self):
        m = parse_api_keys("aaa,bbb")
        assert m["aaa"] == "key_1"
        assert m["bbb"] == "key_2"

    def test_parse_named_keys(self):
        m = parse_api_keys("s1:alice,s2:bob")
        assert m["s1"] == "alice"
        assert m["s2"] == "bob"

    def test_authenticate_ok(self):
        with patch("app.core.security.settings") as s:
            s.API_KEYS = "secret:dev"
            ident = authenticate_api_key("secret")
            assert ident is not None
            assert ident.actor == "dev"

    def test_authenticate_fail(self):
        with patch("app.core.security.settings") as s:
            s.API_KEYS = "secret:dev"
            assert authenticate_api_key("wrong") is None


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_auth_disabled_allows(self):
        with patch("app.core.middleware.settings") as s:
            s.AUTH_ENABLED = False
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/health")
                assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_enabled_blocks_api(self):
        with patch("app.core.middleware.settings") as s, patch(
            "app.core.security.settings"
        ) as ss:
            s.AUTH_ENABLED = True
            ss.AUTH_ENABLED = True
            ss.API_KEYS = "good-key:tester"
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                denied = await c.get("/api/v1/tools")
                assert denied.status_code == 401
                # /tools has no DB dependency — isolates middleware behavior
                ok = await c.get("/api/v1/tools", headers={"X-API-Key": "good-key"})
                assert ok.status_code == 200

    @pytest.mark.asyncio
    async def test_health_public_when_auth_on(self):
        with patch("app.core.middleware.settings") as s:
            s.AUTH_ENABLED = True
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/health")
                assert r.status_code == 200
