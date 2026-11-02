# (c) 2026 AgentFlow-Eval
"""KPI / slow-task API tests.

E15e: UUID temp SQLite; reversible get_db override (no clear());
deps.engine / async_session_factory rebound so record_slow_task(persist=True)
and list_slow_tasks_db cannot touch agentflow_eval.db; AOLS LOG_DB_SINK
disabled; await pending persist tasks before dispose. No fixed ./test_obs.db.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core import dependencies as deps
from app.core.dependencies import get_db
from app.core.observability.slow_tasks import clear_slow_tasks, record_slow_task
from app.main import app
from app.models.base import Base
from app.models.slow_task import SlowTaskEvent  # noqa: F401 — register metadata

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


async def _drain_persist_tasks() -> None:
    """Allow loop.create_task(_write) from record_slow_task to finish."""
    await asyncio.sleep(0)
    pending = [
        t
        for t in asyncio.all_tasks()
        if not t.done() and t is not asyncio.current_task()
    ]
    if pending:
        await asyncio.wait(pending, timeout=2.0)
    await asyncio.sleep(0)


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    from app.core.observability.aols.sinks import db as aols_db_sink

    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)

    db_path = _BACKEND_ROOT / f"test_obs_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_obs.db"

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

    # Critical: _persist_async / list_slow_tasks_db import factory from deps at call time
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
        await _drain_persist_tasks()
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
    # Drain persist create_task before auto source may hit list_slow_tasks_db
    await _drain_persist_tasks()
    r = await api_client.get("/api/v1/observability/slow-tasks")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert r.json()["items"][0]["stage"] == "agent"


@pytest.mark.asyncio
async def test_error_topology(api_client):
    r = await api_client.get("/api/v1/observability/error-topology")
    assert r.status_code == 200
    assert "topology" in r.json()
