# (c) 2026 AgentFlow-Eval
"""Stripe Checkout mock flow tests.

E15d-3B: UUID temp SQLite for ASGI fixture; reversible get_db override
(no clear()); deps.engine / factory rebound; AOLS LOG_DB_SINK disabled.
No fixed ./test_stripe_checkout.db.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core import dependencies as deps
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

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


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
    from app.core.observability.aols.sinks import db as aols_db_sink

    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.STRIPE_MODE", "mock")
    monkeypatch.setattr("app.core.billing.stripe_checkout.settings.STRIPE_MODE", "mock")

    db_path = _BACKEND_ROOT / f"test_stripe_checkout_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_stripe_checkout.db"

    if db_path.exists():
        db_path.unlink()

    engine = create_async_engine(test_db_url, echo=False)
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

    had_get_db = get_db in app.dependency_overrides
    prev_get_db = app.dependency_overrides.get(get_db)
    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))

    deps.engine = engine
    deps.async_session_factory = factory
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = False
    app.dependency_overrides[get_db] = _override

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        if had_get_db:
            app.dependency_overrides[get_db] = prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)
        try:
            with aols_db_sink._lock:
                aols_db_sink._queue.clear()
        except Exception:
            pass
        settings.LOG_DB_SINK = prev_sink
        settings.DATABASE_URL = prev_db_url
        deps.engine = prev_engine
        deps.async_session_factory = prev_factory
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
        try:
            if db_path.exists():
                db_path.unlink()
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
