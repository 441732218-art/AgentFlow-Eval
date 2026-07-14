# (c) 2026 AgentFlow-Eval
"""Tests for /api/v1/settings/actor."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_actor_anonymous_when_auth_off():
    with patch("app.core.middleware.settings") as ms:
        ms.AUTH_ENABLED = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/v1/settings/actor")
            assert r.status_code == 200
            body = r.json()
            assert body["current_actor"] in ("anonymous", "public")
            assert body["auth_enabled"] is False
            assert "is_admin" in body


@pytest.mark.asyncio
async def test_actor_from_api_key():
    with patch("app.core.middleware.settings") as ms, patch(
        "app.core.security.settings"
    ) as ss, patch("app.api.v1.endpoints.settings.settings") as es, patch(
        "app.api.v1.endpoints.settings.is_admin", return_value=True
    ), patch(
        "app.api.v1.endpoints.settings.admin_actors", return_value={"admin"}
    ), patch(
        "app.api.v1.endpoints.settings.parse_api_keys",
        return_value={"ops-secret": "admin"},
    ), patch(
        "app.api.v1.endpoints.settings.authenticate_api_key"
    ) as auth:
        ms.AUTH_ENABLED = True
        ss.AUTH_ENABLED = True
        ss.API_KEYS = "ops-secret:admin"
        es.AUTH_ENABLED = True
        es.API_KEYS = "ops-secret:admin"
        from app.core.security import AuthIdentity

        auth.return_value = AuthIdentity(
            key_id="x", actor="admin", raw_key_prefix="ops-***"
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get(
                "/api/v1/settings/actor", headers={"X-API-Key": "ops-secret"}
            )
            assert r.status_code == 200
            body = r.json()
            assert body["current_actor"] == "admin"
            assert body["is_admin"] is True
