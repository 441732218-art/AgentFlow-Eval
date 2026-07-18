# (c) 2026 AgentFlow-Eval
"""Stripe Checkout mock flow tests."""

from __future__ import annotations

import json
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.billing.stripe_checkout import (
    build_mock_completed_event,
    create_checkout_session,
    parse_checkout_completed_event,
    stripe_mode,
    verify_webhook_signature,
)
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_stripe_checkout.db"


def test_mock_session_shape(monkeypatch):
    monkeypatch.setattr("app.config.settings.STRIPE_MODE", "mock")
    monkeypatch.setattr("app.core.billing.stripe_checkout.settings.STRIPE_MODE", "mock")
    assert stripe_mode() == "mock"
    s = create_checkout_session(
        actor="alice",
        plan_code="pro",
        plan_name="Pro",
        amount_cents=4900,
    )
    assert s["mode"] == "mock"
    assert s["session_id"].startswith("cs_test_mock_")
    assert "url" in s
    assert s["plan_code"] == "pro"


def test_parse_and_verify_mock_event():
    event = build_mock_completed_event(
        actor="bob", plan_code="pro", session_id="cs_test_1"
    )
    parsed = parse_checkout_completed_event(event)
    assert parsed is not None
    assert parsed["actor"] == "bob"
    assert parsed["plan_code"] == "pro"
    assert verify_webhook_signature(json.dumps(event).encode(), None) is True


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.STRIPE_MODE", "mock")
    monkeypatch.setattr("app.core.billing.stripe_checkout.settings.STRIPE_MODE", "mock")

    engine = create_async_engine(TEST_DB, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_stripe_checkout.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_checkout_and_mock_confirm(api_client):
    r = await api_client.post(
        "/api/v1/billing/checkout",
        json={"plan_code": "pro"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["checkout"]["mode"] == "mock"
    sid = body["checkout"]["session_id"]

    conf = await api_client.post(
        "/api/v1/billing/checkout/mock-confirm",
        json={"session_id": sid, "plan_code": "pro"},
    )
    assert conf.status_code == 200, conf.text
    assert conf.json()["subscription"]["status"] == "active"

    q = await api_client.get("/api/v1/billing/quota")
    assert q.status_code == 200
    assert q.json()["plan_code"] == "pro"


@pytest.mark.asyncio
async def test_webhook_activates_subscription(api_client):
    event = build_mock_completed_event(
        actor="anonymous",
        plan_code="enterprise",
        session_id="cs_wh_1",
    )
    r = await api_client.post(
        "/api/v1/billing/webhook/stripe",
        content=json.dumps(event),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["handled"] is True
    q = await api_client.get("/api/v1/billing/quota")
    assert q.json()["plan_code"] == "enterprise"


@pytest.mark.asyncio
async def test_checkout_free_is_direct(api_client):
    r = await api_client.post(
        "/api/v1/billing/checkout",
        json={"plan_code": "free"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("mode") == "direct"
