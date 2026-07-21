# (c) 2026 AgentFlow-Eval
"""API tests for Experiment create / list / compare."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace, TraceStatus

TEST_DB = "sqlite+aiosqlite:///./test_experiments_unit.db"


@pytest_asyncio.fixture
async def api_client():
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
        yield client, factory

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_experiments_unit.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_create_list_compare_experiment(api_client):
    client, factory = api_client

    # base task with suites
    r = await client.post(
        "/api/v1/tasks",
        json={
            "name": "base",
            "description": "",
            "agent_config": {"model": "gpt-4o-mini"},
        },
    )
    assert r.status_code == 201
    base_id = r.json()["id"]
    await client.post(
        f"/api/v1/tasks/{base_id}/test-suites/upload",
        files={
            "file": (
                "c.json",
                b'[{"user_query":"q1","expected_output":"a1","expected_tools":["calculator"]}]',
                "application/json",
            )
        },
    )

    with patch("app.api.v1.endpoints.experiments._queue_task", return_value=None):
        exp = await client.post(
            "/api/v1/experiments",
            json={
                "name": "model-bakeoff",
                "description": "compare two models",
                "base_task_id": base_id,
                "auto_execute": False,
                "variants": [
                    {"label": "mini", "agent_config": {"model": "gpt-4o-mini"}},
                    {
                        "label": "http-v1",
                        "agent_config": {
                            "runner": "http",
                            "endpoint_url": "https://agent.example/run",
                        },
                    },
                ],
            },
        )
    assert exp.status_code == 201, exp.text
    body = exp.json()
    assert body["name"] == "model-bakeoff"
    assert body["suite_count"] == 1
    assert len(body["runs"]) == 2
    labels = {r["label"] for r in body["runs"]}
    assert labels == {"mini", "http-v1"}

    lst = await client.get("/api/v1/experiments")
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1

    exp_id = body["id"]
    detail = await client.get(f"/api/v1/experiments/{exp_id}")
    assert detail.status_code == 200

    # Seed metric scores on first run's task for compare
    run0 = body["runs"][0]
    async with factory() as session:
        from sqlalchemy import select

        suite = (
            await session.execute(
                select(TestSuite).where(TestSuite.task_id == run0["task_id"])
            )
        ).scalar_one()
        trace = Trace(
            test_suite_id=suite.id,
            user_query=suite.user_query,
            steps=[],
            total_tokens=10,
            response_time_ms=50,
            status=TraceStatus.SUCCESS,
        )
        session.add(trace)
        await session.flush()
        for name, score in (
            ("tool_accuracy", 40.0),
            ("answer_correctness", 40.0),
            ("reasoning_coherence", 20.0),
        ):
            session.add(
                MetricScore(
                    trace_id=trace.id,
                    metric_name=name,
                    score=score,
                    reason="test",
                )
            )
        task = (
            await session.execute(select(Task).where(Task.id == run0["task_id"]))
        ).scalar_one()
        task.status = TaskStatus.COMPLETED
        await session.commit()

    cmp = await client.get(f"/api/v1/experiments/{exp_id}/compare")
    assert cmp.status_code == 200, cmp.text
    data = cmp.json()
    assert data["experiment_id"] == exp_id
    assert len(data["runs"]) == 2
    scored = next(r for r in data["runs"] if r["label"] == run0["label"])
    assert scored["average_score"] == 100.0
    assert data["best_label"] == run0["label"]


@pytest.mark.asyncio
async def test_create_requires_suites(api_client):
    client, _ = api_client
    r = await client.post(
        "/api/v1/experiments",
        json={
            "name": "empty",
            "auto_execute": False,
            "variants": [{"label": "a", "agent_config": {}}],
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_labels_rejected(api_client):
    client, _ = api_client
    r = await client.post(
        "/api/v1/experiments",
        json={
            "name": "dup",
            "suites": [{"user_query": "q", "expected_output": "a"}],
            "auto_execute": False,
            "variants": [
                {"label": "same", "agent_config": {}},
                {"label": "same", "agent_config": {"model": "x"}},
            ],
        },
    )
    assert r.status_code == 422
