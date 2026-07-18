# (c) 2026 AgentFlow-Eval
"""KPI / slow-task API tests."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.observability.slow_tasks import clear_slow_tasks, record_slow_task
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_obs.db"


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
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
        os.remove("./test_obs.db")
    except OSError:
        pass
    clear_slow_tasks()


@pytest.mark.asyncio
async def test_kpis_endpoint(api_client):
    r = await api_client.get("/api/v1/observability/kpis?days=7")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert "kpis" in body
    assert "success_rate" in body["kpis"] or body["kpis"]["tasks_total"] == 0


@pytest.mark.asyncio
async def test_slow_tasks_endpoint(api_client):
    clear_slow_tasks()
    assert record_slow_task(
        stage="agent", duration_sec=99.0, threshold_sec=30.0, status="ok"
    )
    r = await api_client.get("/api/v1/observability/slow-tasks")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert r.json()["items"][0]["stage"] == "agent"


@pytest.mark.asyncio
async def test_error_topology(api_client):
    r = await api_client.get("/api/v1/observability/error-topology")
    assert r.status_code == 200
    assert "topology" in r.json()
