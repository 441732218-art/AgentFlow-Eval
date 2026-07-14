# (c) 2026 AgentFlow-Eval
"""Trace API ownership isolation tests."""

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
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace, TraceStatus

TEST_DB = "sqlite+aiosqlite:///./test_traces_tenancy.db"


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
        os.remove("./test_traces_tenancy.db")
    except OSError:
        pass


async def _seed_owned_trace(factory, owner: str, query: str = "q"):
    async with factory() as session:
        task = Task(
            name=f"task-{owner}",
            description="",
            agent_config={},
            status=TaskStatus.COMPLETED,
            created_by=owner,
        )
        session.add(task)
        await session.flush()
        suite = TestSuite(
            task_id=task.id,
            user_query=query,
            expected_output="ans",
            expected_tools=["calculator"],
        )
        session.add(suite)
        await session.flush()
        trace = Trace(
            test_suite_id=suite.id,
            user_query=query,
            steps=[{"thought": "t", "action": "final_answer", "action_input": "42"}],
            total_tokens=10,
            response_time_ms=100,
            status=TraceStatus.SUCCESS,
        )
        session.add(trace)
        await session.commit()
        return task.id, suite.id, trace.id


@pytest.mark.asyncio
async def test_trace_isolation_between_actors(api_client):
    client, factory = api_client
    _, _, alice_trace = await _seed_owned_trace(factory, "alice", "alice-q")
    _, _, bob_trace = await _seed_owned_trace(factory, "bob", "bob-q")

    with patch("app.core.middleware.settings") as ms, patch(
        "app.core.security.settings"
    ) as ss, patch("app.core.tenancy.settings") as ts:
        ms.AUTH_ENABLED = True
        ss.AUTH_ENABLED = True
        ss.API_KEYS = "alice-key:alice,bob-key:bob,admin-key:admin"
        ts.AUTH_ENABLED = True
        ts.TENANCY_ENABLED = False
        ts.ADMIN_ACTORS = "admin"

        # Alice sees only her traces
        la = await client.get("/api/v1/traces", headers={"X-API-Key": "alice-key"})
        assert la.status_code == 200, la.text
        a_ids = {i["id"] for i in la.json()["items"]}
        assert alice_trace in a_ids
        assert bob_trace not in a_ids

        # Alice cannot open bob's trace
        denied = await client.get(
            f"/api/v1/traces/{bob_trace}", headers={"X-API-Key": "alice-key"}
        )
        assert denied.status_code == 404

        # Alice can open her own
        ok = await client.get(
            f"/api/v1/traces/{alice_trace}", headers={"X-API-Key": "alice-key"}
        )
        assert ok.status_code == 200
        assert ok.json()["id"] == alice_trace

        # Admin sees both
        admin = await client.get("/api/v1/traces", headers={"X-API-Key": "admin-key"})
        assert admin.status_code == 200
        admin_ids = {i["id"] for i in admin.json()["items"]}
        assert alice_trace in admin_ids
        assert bob_trace in admin_ids


@pytest.mark.asyncio
async def test_judge_and_review_access(api_client):
    client, factory = api_client
    _, _, alice_trace = await _seed_owned_trace(factory, "alice")
    _, _, bob_trace = await _seed_owned_trace(factory, "bob")

    with patch("app.core.middleware.settings") as ms, patch(
        "app.core.security.settings"
    ) as ss, patch("app.core.tenancy.settings") as ts:
        ms.AUTH_ENABLED = True
        ss.AUTH_ENABLED = True
        ss.API_KEYS = "alice-key:alice,bob-key:bob"
        ts.AUTH_ENABLED = True
        ts.TENANCY_ENABLED = False
        ts.ADMIN_ACTORS = "admin"

        # Rule-based judge (no API key on LLMJudge -> rule only)
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            j = await client.post(
                f"/api/v1/traces/{alice_trace}/judge",
                headers={"X-API-Key": "alice-key"},
            )
        assert j.status_code == 200, j.text
        assert "scores" in j.json()

        # Bob cannot judge alice's trace
        denied = await client.post(
            f"/api/v1/traces/{alice_trace}/judge",
            headers={"X-API-Key": "bob-key"},
        )
        assert denied.status_code == 404

        # Alice can human-review
        rev = await client.post(
            f"/api/v1/traces/{alice_trace}/review",
            headers={"X-API-Key": "alice-key"},
            json={
                "metric_name": "answer_correctness",
                "human_score": 35,
                "reviewer": "alice",
                "reason": "ok",
            },
        )
        assert rev.status_code == 200, rev.text
        assert rev.json()["is_human_reviewed"] is True

        # Bob cannot review alice
        denied_r = await client.post(
            f"/api/v1/traces/{alice_trace}/review",
            headers={"X-API-Key": "bob-key"},
            json={
                "metric_name": "answer_correctness",
                "human_score": 10,
                "reviewer": "bob",
            },
        )
        assert denied_r.status_code == 404


@pytest.mark.asyncio
async def test_report_isolation(api_client):
    client, factory = api_client
    alice_task, _, _ = await _seed_owned_trace(factory, "alice")
    bob_task, _, _ = await _seed_owned_trace(factory, "bob")

    with patch("app.core.middleware.settings") as ms, patch(
        "app.core.security.settings"
    ) as ss, patch("app.core.tenancy.settings") as ts:
        ms.AUTH_ENABLED = True
        ss.AUTH_ENABLED = True
        ss.API_KEYS = "alice-key:alice,bob-key:bob"
        ts.AUTH_ENABLED = True
        ts.TENANCY_ENABLED = False
        ts.ADMIN_ACTORS = "admin"

        ok = await client.get(
            f"/api/v1/reports/{alice_task}", headers={"X-API-Key": "alice-key"}
        )
        assert ok.status_code == 200

        denied = await client.get(
            f"/api/v1/reports/{bob_task}", headers={"X-API-Key": "alice-key"}
        )
        assert denied.status_code == 404
