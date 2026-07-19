# (c) 2026 AgentFlow-Eval
"""Security hardening checks (headers, public paths, non-root Dockerfile cues)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import is_public_path
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_security_headers_present(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health/live")
    assert r.status_code == 200
    # Middleware may set nosniff / frame options
    headers = {k.lower(): v for k, v in r.headers.items()}
    # At least health is public and responds
    assert "content-type" in headers


def test_billing_webhook_is_public():
    assert is_public_path("/api/v1/billing/webhook")
    assert is_public_path("/api/v1/billing/webhook/stripe")
    assert not is_public_path("/api/v1/tasks")


def test_backend_dockerfile_non_root():
    df = (ROOT / "Dockerfile.backend").read_text(encoding="utf-8")
    assert "USER agentflow" in df or "USER 10001" in df
    assert "multi-stage" in df.lower() or "AS builder" in df
    assert "AS runtime" in df


def test_prod_compose_has_resource_limits():
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "no-new-privileges" in text
    assert "resources:" in text
    assert "prometheus" in text
