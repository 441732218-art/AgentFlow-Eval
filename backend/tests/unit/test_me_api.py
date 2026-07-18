# (c) 2026 AgentFlow-Eval
"""API tests for /me identity + permissions contract."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.rbac import Permission, ROLE_PERMISSIONS, Role


@pytest_asyncio.fixture
async def client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_me_returns_permissions_when_auth_off(client):
    r = await client.get("/api/v1/me")
    assert r.status_code == 200
    body = r.json()
    assert "actor" in body
    assert "role" in body
    assert "permissions" in body
    assert isinstance(body["permissions"], list)
    assert body["rbac_enforced"] is False
    # Unrestricted local → admin-equivalent full set
    assert "task:read" in body["permissions"]


@pytest.mark.asyncio
async def test_me_permissions_endpoint(client):
    r = await client.get("/api/v1/me/permissions")
    assert r.status_code == 200
    body = r.json()
    assert "permissions" in body
    assert "role" in body


@pytest.mark.asyncio
async def test_me_trace_header_echo(client):
    r = await client.get("/api/v1/me", headers={"X-Request-ID": "trace-abc-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "trace-abc-123"
    assert r.headers.get("X-Trace-ID") == "trace-abc-123"
    assert r.json().get("request_id") == "trace-abc-123"


def test_frontend_permission_strings_cover_backend_enum():
    """Contract: frontend ALL_PERMISSIONS must match backend Permission values."""
    backend = {p.value for p in Permission}
    # Mirror frontend/src/auth/permissions.ts — keep in sync
    frontend = {
        "task:create",
        "task:read",
        "task:update",
        "task:delete",
        "task:execute",
        "task:cancel",
        "evaluation:read",
        "evaluation:submit",
        "evaluation:approve",
        "user:manage",
        "system:config",
        "audit:read",
    }
    assert backend == frontend


def test_role_matrices_non_empty():
    for role in Role:
        assert len(ROLE_PERMISSIONS[role]) >= 1
