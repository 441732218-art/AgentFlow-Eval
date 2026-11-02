# (c) 2026 AgentFlow-Eval
"""API tests for online A/B framework.

E15d-3D: UUID temp SQLite; reversible get_db override (no clear());
deps.engine / factory rebound; AOLS LOG_DB_SINK disabled. No fixed
./test_ab_api.db.
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
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    from app.core.observability.aols.sinks import db as aols_db_sink

    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)

    db_path = _BACKEND_ROOT / f"test_ab_api_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_ab_api.db"

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


def _create_body(**kwargs):
    base = {
        "key": "prompt_v2",
        "name": "Prompt AB",
        "description": "test",
        "primary_metric": "conversion",
        "alpha": 0.05,
        "min_sample_size": 10,
        "start_immediately": True,
        "variants": [
            {
                "key": "control",
                "name": "Control",
                "weight": 1,
                "is_control": True,
                "payload": {"model": "gpt-4o-mini"},
            },
            {
                "key": "treatment",
                "name": "Treatment",
                "weight": 1,
                "is_control": False,
                "payload": {"model": "gpt-4o"},
            },
        ],
    }
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_assign_track_results(api_client):
    r = await api_client.post("/api/v1/ab", json=_create_body())
    assert r.status_code == 201, r.text
    exp = r.json()
    assert exp["status"] == "running"
    assert len(exp["variants"]) == 2
    exp_id = exp["id"]
    key = exp["key"]

    # sticky assign
    a1 = await api_client.post(
        f"/api/v1/ab/{key}/assign",
        json={"unit_id": "user-1", "record_exposure": True},
    )
    assert a1.status_code == 200, a1.text
    v1 = a1.json()["variant_key"]
    a2 = await api_client.post(
        f"/api/v1/ab/{key}/assign",
        json={"unit_id": "user-1"},
    )
    assert a2.json()["variant_key"] == v1
    assert a2.json()["is_new"] is False

    # conversions for many units
    for i in range(30):
        uid = f"u{i}"
        await api_client.post(
            f"/api/v1/ab/{key}/assign",
            json={"unit_id": uid, "record_exposure": True},
        )
        # convert half
        if i % 2 == 0:
            tr = await api_client.post(
                f"/api/v1/ab/{key}/track",
                json={"unit_id": uid, "event_type": "conversion"},
            )
            assert tr.status_code == 200, tr.text

    results = await api_client.get(f"/api/v1/ab/{exp_id}/results")
    assert results.status_code == 200, results.text
    body = results.json()
    assert body["key"] == key
    assert len(body["variants"]) == 2
    assert "conversion_rate" in body["variants"][0]


@pytest.mark.asyncio
async def test_sample_size(api_client):
    r = await api_client.post(
        "/api/v1/ab/sample-size",
        json={"baseline_rate": 0.1, "mde": 0.02, "alpha": 0.05, "power": 0.8},
    )
    assert r.status_code == 200, r.text
    assert r.json()["per_variant"] > 50


@pytest.mark.asyncio
async def test_pause_blocks_new_assign(api_client):
    r = await api_client.post("/api/v1/ab", json=_create_body(key="paused_exp"))
    exp_id = r.json()["id"]
    key = r.json()["key"]
    await api_client.patch(
        f"/api/v1/ab/{exp_id}/status",
        json={"status": "paused"},
    )
    bad = await api_client.post(
        f"/api/v1/ab/{key}/assign",
        json={"unit_id": "new-user"},
    )
    assert bad.status_code in (400, 409, 422) or bad.status_code == 400
