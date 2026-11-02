# (c) 2026 AgentFlow-Eval
"""API tests for tasks CRUD, upload, archive, and actor isolation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
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
from app.models.task import Task, TaskStatus

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest_asyncio.fixture
async def api_env():
    """ASGI client bound to a unique temporary SQLite DB (E13b isolation).

    After E13a index dedupe, Base.metadata.create_all is safe on SQLite.
    Does not mutate Base.metadata indexes; does not use fixed test_tasks_unit.db.
    Also rebinds deps.engine / async_session_factory so accidental default-engine
    use cannot create agentflow_eval.db (httpx 0.27 ASGITransport has no lifespan).
    """
    db_path = _BACKEND_ROOT / f"test_tasks_api_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert "test_tasks_unit.db" not in test_db_url
    assert db_path.name.startswith("test_tasks_api_")

    index_fingerprint_before = {
        t.name: sorted(i.name or "" for i in t.indexes)
        for t in Base.metadata.tables.values()
    }

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

    from app.core.observability.aols.sinks import db as aols_db_sink

    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_log_db_sink = bool(getattr(settings, "LOG_DB_SINK", True))
    # This fixture owns only get_db; snapshot before install (E15h-2).
    had_get_db = get_db in app.dependency_overrides
    prev_get_db = app.dependency_overrides.get(get_db)
    deps.engine = engine
    deps.async_session_factory = factory
    # Prevent AOLS sync sink / atexit flush from creating agentflow_eval.db
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = False
    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield SimpleNamespace(
                client=client,
                db_path=db_path,
                db_url=test_db_url,
                factory=factory,
            )
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
        settings.LOG_DB_SINK = prev_log_db_sink
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
        index_fingerprint_after = {
            t.name: sorted(i.name or "" for i in t.indexes)
            for t in Base.metadata.tables.values()
        }
        assert index_fingerprint_before == index_fingerprint_after, (
            "Fixture must not mutate Base.metadata indexes"
        )


@pytest_asyncio.fixture
async def api_client(api_env):
    return api_env.client


@pytest.mark.asyncio
async def test_create_and_list_task(api_client):
    r = await api_client.post(
        "/api/v1/tasks",
        json={
            "name": "demo",
            "description": "d",
            "agent_config": {"model": "gpt-4o-mini"},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "demo"
    assert body["status"] == "created"
    assert body.get("created_by") == "anonymous"
    assert body["is_archived"] is False

    lst = await api_client.get("/api/v1/tasks")
    assert lst.status_code == 200
    data = lst.json()
    assert data["total"] >= 1
    assert any(i["id"] == body["id"] for i in data["items"])


@pytest.mark.asyncio
async def test_upload_csv_suites(api_client):
    r = await api_client.post(
        "/api/v1/tasks",
        json={"name": "upload-me", "description": "", "agent_config": {}},
    )
    tid = r.json()["id"]
    csv_body = "user_query,expected_output,expected_tools\nq1,a1,calculator\nq2,a2,web_search\n"
    u = await api_client.post(
        f"/api/v1/tasks/{tid}/test-suites/upload",
        files={"file": ("cases.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert u.status_code == 201, u.text
    assert u.json()["created"] == 2


@pytest.mark.asyncio
async def test_upload_json_suites(api_client):
    r = await api_client.post(
        "/api/v1/tasks",
        json={"name": "json-up", "description": "", "agent_config": {}},
    )
    tid = r.json()["id"]
    payload = b'[{"user_query":"hi","expected_output":"hello","expected_tools":["web_search"]}]'
    u = await api_client.post(
        f"/api/v1/tasks/{tid}/test-suites/upload",
        files={"file": ("cases.json", payload, "application/json")},
    )
    assert u.status_code == 201
    assert u.json()["created"] == 1


@pytest.mark.asyncio
async def test_archive_requires_terminal(api_client):
    r = await api_client.post(
        "/api/v1/tasks",
        json={"name": "arch", "description": "", "agent_config": {}},
    )
    tid = r.json()["id"]
    a = await api_client.post(f"/api/v1/tasks/{tid}/archive")
    assert a.status_code == 409


@pytest.mark.asyncio
async def test_archive_success(api_env):
    """Directly mark completed then archive (same temp DB as api_client)."""
    client = api_env.client
    r = await client.post(
        "/api/v1/tasks",
        json={"name": "done", "description": "", "agent_config": {}},
    )
    tid = r.json()["id"]

    async with api_env.factory() as session:
        task = await session.get(Task, tid)
        task.status = TaskStatus.COMPLETED
        await session.commit()

    a = await client.post(f"/api/v1/tasks/{tid}/archive")
    assert a.status_code == 200, a.text
    assert a.json()["is_archived"] is True

    # Hidden from default list
    lst = await client.get("/api/v1/tasks")
    ids = [i["id"] for i in lst.json()["items"]]
    assert tid not in ids

    # Visible with include_archived
    lst2 = await client.get("/api/v1/tasks", params={"include_archived": True})
    ids2 = [i["id"] for i in lst2.json()["items"]]
    assert tid in ids2


@pytest.mark.asyncio
async def test_actor_isolation(api_client):
    """With AUTH+tenancy, alice cannot see bob's tasks."""
    with (
        patch("app.core.middleware.settings") as ms,
        patch("app.core.security.settings") as ss,
        patch("app.core.tenancy.settings") as ts,
    ):
        ms.AUTH_ENABLED = True
        ss.AUTH_ENABLED = True
        ss.API_KEYS = "alice-key:alice,bob-key:bob,admin-key:admin"
        ts.AUTH_ENABLED = True
        ts.TENANCY_ENABLED = False
        ts.ADMIN_ACTORS = "admin"

        # Alice creates
        r1 = await api_client.post(
            "/api/v1/tasks",
            json={"name": "alice-task", "description": "", "agent_config": {}},
            headers={"X-API-Key": "alice-key"},
        )
        assert r1.status_code == 201, r1.text
        alice_tid = r1.json()["id"]
        assert r1.json()["created_by"] == "alice"

        # Bob creates
        r2 = await api_client.post(
            "/api/v1/tasks",
            json={"name": "bob-task", "description": "", "agent_config": {}},
            headers={"X-API-Key": "bob-key"},
        )
        assert r2.status_code == 201
        bob_tid = r2.json()["id"]

        # Alice list: only hers
        la = await api_client.get("/api/v1/tasks", headers={"X-API-Key": "alice-key"})
        assert la.status_code == 200
        a_ids = {i["id"] for i in la.json()["items"]}
        assert alice_tid in a_ids
        assert bob_tid not in a_ids

        # Alice cannot get bob's task
        denied = await api_client.get(
            f"/api/v1/tasks/{bob_tid}", headers={"X-API-Key": "alice-key"}
        )
        assert denied.status_code == 404

        # Admin sees both
        admin_list = await api_client.get(
            "/api/v1/tasks", headers={"X-API-Key": "admin-key"}
        )
        assert admin_list.status_code == 200
        admin_ids = {i["id"] for i in admin_list.json()["items"]}
        assert alice_tid in admin_ids
        assert bob_tid in admin_ids


@pytest.mark.asyncio
async def test_tools_list_and_probe(api_client):
    r = await api_client.get("/api/v1/tools")
    assert r.status_code == 200
    assert r.json()["total"] >= 2

    p = await api_client.post(
        "/api/v1/tools/probe",
        json={"name": "calculator", "args": {"expression": "2+3"}},
    )
    assert p.status_code == 200
    assert "5" in p.json()["output"]


@pytest.mark.asyncio
async def test_execute_queues(api_client):
    r = await api_client.post(
        "/api/v1/tasks",
        json={"name": "run", "description": "", "agent_config": {}},
    )
    tid = r.json()["id"]

    from app.core.ports.task_queue import EnqueueResult

    mock_queue = MagicMock()
    mock_queue.enqueue.return_value = EnqueueResult(
        task_id="celery-123", backend="celery", eager=False
    )
    # execute_task does: from app.core.profiles import get_task_queue
    with patch("app.core.profiles.get_task_queue", return_value=mock_queue):
        ex = await api_client.post(f"/api/v1/tasks/{tid}/execute")
    assert ex.status_code == 200, ex.text
    assert ex.json()["status"] == "queued"
    assert ex.json()["celery_task_id"] == "celery-123"
    mock_queue.enqueue.assert_called_once()
    assert mock_queue.enqueue.call_args.args[0] == "run_full_evaluation"
