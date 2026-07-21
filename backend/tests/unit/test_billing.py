# (c) 2026 AgentFlow-Eval
"""Billing service unit tests."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.billing.service import (
    QuotaExceededError,
    get_billing_service,
    period_key,
)
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_billing.db"


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(TEST_DB, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_billing.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_ensure_plans_and_quota(session):
    svc = get_billing_service()
    n = await svc.ensure_default_plans(session)
    assert n >= 3
    n2 = await svc.ensure_default_plans(session)
    assert n2 == 0
    q = await svc.get_quota(session, "alice")
    assert q["period"] == period_key()
    assert q["task_limit"] > 0
    assert q["token_limit"] > 0


@pytest.mark.asyncio
async def test_subscribe_and_usage(session):
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    sub = await svc.subscribe(session, actor="bob", plan_code="pro")
    assert sub.status == "active"
    await svc.record_usage(
        session, actor="bob", metric="task", quantity=1, ref_type="task", ref_id="t1"
    )
    # With billing off, quota not consumed unless enabled
    q = await svc.get_quota(session, "bob")
    assert q["plan_code"] == "pro"


@pytest.mark.asyncio
async def test_quota_exceeded_when_billing_on(session, monkeypatch):
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", True)
    monkeypatch.setattr(
        "app.core.billing.service.billing_enabled", lambda: True
    )
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    await svc.subscribe(session, actor="carol", plan_code="free")
    bal = await svc._get_or_create_balance(session, "carol")
    bal.task_used = bal.task_limit
    await session.flush()
    with pytest.raises(QuotaExceededError) as ei:
        await svc.ensure_task_quota(session, "carol")
    assert ei.value.status_code == 429
    detail = ei.value.detail or {}
    assert isinstance(detail, dict)
    assert detail.get("code") == "QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_get_current_plan_and_limits(session, monkeypatch):
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", True)
    monkeypatch.setattr("app.core.billing.service.billing_enabled", lambda: True)
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    await svc.subscribe(session, actor="dana", plan_code="pro")
    plan = await svc.get_current_plan(session, "dana")
    assert plan["plan"]["code"] == "pro"
    assert plan["quota"]["task_limit"] >= 1000
    assert "storage_limit_mb" in plan["quota"]
    assert "plugin_limit" in plan["quota"]
    assert plan["quota"]["limits"]["tasks"] == plan["quota"]["task_limit"]


@pytest.mark.asyncio
async def test_billing_plan_api(api_client):
    r = await api_client.get("/api/v1/billing/plans")
    assert r.status_code == 200
    assert r.json()["total"] >= 3
    r2 = await api_client.get("/api/v1/billing/plan")
    assert r2.status_code == 200
    body = r2.json()
    assert "plan" in body and "quota" in body


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)

    engine = create_async_engine(TEST_DB + ".api", echo=False)
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
        os.remove("./test_billing.db.api")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_billing_plans_api(api_client):
    r = await api_client.get("/api/v1/billing/plans")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 3
    codes = {p["code"] for p in body["items"]}
    assert "free" in codes and "pro" in codes


@pytest.mark.asyncio
async def test_billing_quota_api(api_client):
    r = await api_client.get("/api/v1/billing/quota")
    assert r.status_code == 200
    assert "token_limit" in r.json()
