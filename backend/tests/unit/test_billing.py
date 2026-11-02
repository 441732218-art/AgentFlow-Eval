# (c) 2026 AgentFlow-Eval
"""Billing service unit tests.

E15d-3A: UUID temp SQLite for service + ASGI fixtures; reversible get_db
override (no clear()); deps.engine / factory rebound and AOLS sink disabled
for ASGI. No fixed ./test_billing.db or ./test_billing.db.api.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core import dependencies as deps
from app.core.billing.service import (
    QuotaExceededError,
    get_billing_service,
    period_key,
)
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest_asyncio.fixture
async def session():
    db_path = _BACKEND_ROOT / f"test_billing_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_billing.db"

    if db_path.exists():
        db_path.unlink()

    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        if db_path.exists():
            db_path.unlink()
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
    monkeypatch.setattr("app.core.billing.service.billing_enabled", lambda: True)
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
    from app.core.observability.aols.sinks import db as aols_db_sink

    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)

    db_path = _BACKEND_ROOT / f"test_billing_api_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_billing.db.api"

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
