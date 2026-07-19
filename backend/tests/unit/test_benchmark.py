# (c) 2026 AgentFlow-Eval
"""Benchmark platform unit tests."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.benchmark.service import get_benchmark_service
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base
from app.models.metric_score import MetricScore
from app.models.task import TaskStatus
from app.models.trace import Trace, TraceStatus

TEST_DB = "sqlite+aiosqlite:///./test_benchmark.db"


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
        os.remove("./test_benchmark.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_create_import_run_leaderboard(session, monkeypatch):
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)

    svc = get_benchmark_service()
    bm = await svc.create_benchmark(
        session,
        name="demo-bench",
        description="unit",
        created_by="alice",
        cases=[
            {
                "name": "c1",
                "user_query": "hello",
                "expected_output": "world",
            },
            {
                "name": "c2",
                "user_query": "ping",
                "expected_output": "pong",
            },
        ],
    )
    assert bm.id
    full = await svc.get_benchmark(session, bm.id)
    assert len(full.cases) == 2

    # CSV import
    csv_body = "name,user_query,expected_output\nc3,foo,bar\n"
    rows = svc.parse_import_payload(content=csv_body, fmt="csv")
    await svc.add_cases(session, bm, rows)
    full = await svc.get_benchmark(session, bm.id)
    assert len(full.cases) == 3

    # Run without enqueue to avoid worker dependency
    run = await svc.run_benchmark(
        session,
        benchmark_id=bm.id,
        actor="alice",
        label="model-a",
        agent_config={"model": "test"},
        enqueue=False,
    )
    assert run.task_id
    assert run.status in {"pending", "queued", "running"}

    # Simulate completed evaluation: add traces + scores
    from app.models.test_suite import TestSuite
    from sqlalchemy import select

    suites = (
        await session.execute(select(TestSuite).where(TestSuite.task_id == run.task_id))
    ).scalars().all()
    assert len(suites) >= 2
    for suite in suites:
        tr = Trace(
            test_suite_id=suite.id,
            user_query=suite.user_query,
            steps=[],
            total_tokens=100,
            response_time_ms=250,
            status=TraceStatus.SUCCESS,
            cost=0.01,
        )
        session.add(tr)
        await session.flush()
        session.add(
            MetricScore(
                trace_id=tr.id,
                metric_name="accuracy",
                score=80.0,
                reason="ok",
            )
        )
        session.add(
            MetricScore(
                trace_id=tr.id,
                metric_name="quality",
                score=90.0,
                reason="ok",
            )
        )

    from app.models.task import Task

    task = (
        await session.execute(select(Task).where(Task.id == run.task_id))
    ).scalar_one()
    task.status = TaskStatus.COMPLETED
    await session.flush()

    run2 = await svc.finalize_run(session, run.id)
    assert run2.status == "completed"
    assert run2.summary.get("tokens", 0) >= 100
    assert run2.summary.get("accuracy") is not None

    board = await svc.leaderboard(session, bm.id)
    assert len(board) >= 1
    assert board[0]["label"] == "model-a"
    assert board[0]["rank"] == 1


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)
    monkeypatch.setattr("app.config.settings.MULTI_TENANT_ENABLED", False)

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
        os.remove("./test_benchmark.db.api")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_benchmark_api(api_client: AsyncClient):
    r = await api_client.post(
        "/api/v1/benchmarks",
        json={
            "name": "api-bench",
            "cases": [{"user_query": "q1", "expected_output": "a1"}],
        },
    )
    assert r.status_code == 201, r.text
    bm_id = r.json()["id"]

    r2 = await api_client.get("/api/v1/benchmarks")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1

    r3 = await api_client.post(
        f"/api/v1/benchmarks/{bm_id}/run",
        json={"label": "v1", "enqueue": False, "agent_config": {"model": "x"}},
    )
    assert r3.status_code == 201, r3.text
    assert r3.json()["run"]["task_id"]

    r4 = await api_client.get(f"/api/v1/benchmarks/{bm_id}/leaderboard")
    assert r4.status_code == 200
    assert "items" in r4.json()
