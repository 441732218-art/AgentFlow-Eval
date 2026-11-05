# (c) 2026 AgentFlow-Eval
"""Scenario: create task → execute (mocked queue) → inspect me/kpis (lite-friendly).

E15d-3G: UUID temp SQLite; reversible get_db override (no clear());
deps.engine / factory rebound; AOLS LOG_DB_SINK disabled. No fixed
./test_scenario_lite.db. Task queue remains mocked (no external worker).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core import dependencies as deps
from app.core.dependencies import get_db
from app.core.ports.task_queue import EnqueueResult
from app.main import app
from app.models.base import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest_asyncio.fixture
async def client(monkeypatch):
    from app.core.observability.aols.sinks import db as aols_db_sink

    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)
    monkeypatch.setattr("app.config.settings.DEPLOY_PROFILE", "lite")
    monkeypatch.setattr("app.config.settings.CELERY_TASK_ALWAYS_EAGER", True)

    db_path = _BACKEND_ROOT / f"test_scenario_lite_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_scenario_lite.db"

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
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
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
