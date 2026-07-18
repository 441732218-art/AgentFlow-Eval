# (c) 2026 AgentFlow-Eval
"""Scenario: create task → execute (mocked queue) → inspect me/kpis (lite-friendly)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.ports.task_queue import EnqueueResult
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_scenario_lite.db"


@pytest_asyncio.fixture
async def client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)
    monkeypatch.setattr("app.config.settings.DEPLOY_PROFILE", "lite")
    monkeypatch.setattr("app.config.settings.CELERY_TASK_ALWAYS_EAGER", True)

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
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_scenario_lite.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_happy_path_create_execute_me_kpis(client):
    me = await client.get("/api/v1/me")
    assert me.status_code == 200
    assert "permissions" in me.json()

    created = await client.post(
        "/api/v1/tasks",
        json={"name": "scenario-lite", "description": "e2e", "agent_config": {}},
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    mock_q = MagicMock()
    mock_q.enqueue.return_value = EnqueueResult(
        task_id="job-1", backend="eager", eager=True
    )
    with patch("app.core.profiles.get_task_queue", return_value=mock_q):
        ex = await client.post(f"/api/v1/tasks/{tid}/execute")
    assert ex.status_code == 200, ex.text
    assert ex.json()["status"] == "queued"

    kpis = await client.get("/api/v1/observability/kpis")
    assert kpis.status_code == 200
    assert kpis.json()["enabled"] is True

    plans = await client.get("/api/v1/billing/plans")
    assert plans.status_code == 200
    assert plans.json()["total"] >= 1
