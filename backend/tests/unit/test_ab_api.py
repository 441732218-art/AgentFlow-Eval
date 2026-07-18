# (c) 2026 AgentFlow-Eval
"""API tests for online A/B framework."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_ab_api.db"


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
        os.remove("./test_ab_api.db")
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
