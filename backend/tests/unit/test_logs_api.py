# (c) 2026 AgentFlow-Eval
"""AOLS logs API + DB sink (Phase 4).

E15g-3: UUID temp SQLite; LOG_DB_SINK remains True so flush_agent_logs_sync
persists via settings.DATABASE_URL into the isolated DB; get_db override
reversible (no clear()); deps.engine / async_session_factory rebound;
queue snapshotted and restored; unlink only owned UUID files.
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
from app.core.observability.aols.emit import emit_evaluation, emit_tool
from app.core.observability.aols.events import LogEvent
from app.core.observability.aols.sinks.db import (
    enqueue_agent_log,
    flush_agent_logs_sync,
    reset_sink_for_tests,
)
from app.core.observability.aols.sinks import db as aols_db_sink
from app.main import app
from app.models.base import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest_asyncio.fixture
async def client():
    db_path = _BACKEND_ROOT / f"test_agent_logs_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_agent_logs.db"
    owned = not db_path.exists()

    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with Session() as session:
            yield session

    had_get_db = get_db in app.dependency_overrides
    prev_get_db = app.dependency_overrides.get(get_db)
    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))

    # Snapshot shared queue so we do not discard other tests' pending rows forever
    with aols_db_sink._lock:
        prev_queue = list(aols_db_sink._queue)
        aols_db_sink._queue.clear()

    # Critical: flush_agent_logs_sync builds sync engine from settings.DATABASE_URL
    deps.engine = engine
    deps.async_session_factory = Session
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = True
    app.dependency_overrides[get_db] = _override

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Drain any rows still queued into the UUID DB before restoring URL
        try:
            flush_agent_logs_sync(limit=500)
        except Exception:
            pass
        with aols_db_sink._lock:
            aols_db_sink._queue.clear()
            aols_db_sink._queue.extend(prev_queue)

        if had_get_db:
            app.dependency_overrides[get_db] = prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)

        settings.LOG_DB_SINK = prev_sink
        settings.DATABASE_URL = prev_db_url
        deps.engine = prev_engine
        deps.async_session_factory = prev_factory

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
        if owned and db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass


class TestLogSink:
    def test_enqueue_and_flush(self, tmp_path, monkeypatch):
        reset_sink_for_tests()
        db_path = tmp_path / "sink.db"
        url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        monkeypatch.setattr("app.config.settings.DATABASE_URL", url)
        monkeypatch.setattr("app.config.settings.LOG_DB_SINK", True)
        from sqlalchemy import create_engine
        from app.models.agent_log import AgentLog
        from app.models.base import Base as ModelBase

        eng = create_engine(f"sqlite:///{db_path.as_posix()}")
        ModelBase.metadata.create_all(eng, tables=[AgentLog.__table__])
        eng.dispose()

        enqueue_agent_log(
            event="test.event",
            level="info",
            task_id="task-abc",
            trace_id="trace-xyz",
            payload={"hello": "world", "password": "secret"},
        )
        n = flush_agent_logs_sync(limit=100)
        assert n >= 1
        assert db_path.exists()


class TestLogsAPI:
    @pytest.mark.asyncio
    async def test_list_and_statistics(self, client) -> None:
        reset_sink_for_tests()
        assert settings.LOG_DB_SINK is True
        emit_evaluation(LogEvent.EVALUATION_STARTED, task_id="t-logs-1")
        emit_tool(
            LogEvent.TOOL_COMPLETED,
            tool_name="calculator",
            latency_ms=5,
            success=True,
            input_data={"x": 1},
            output_data="2",
        )
        n = flush_agent_logs_sync(limit=50)
        assert n >= 1

        r = await client.get("/api/v1/logs", params={"page": 1, "page_size": 20})
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert body["page"] == 1
        assert body["total"] >= 1

        s = await client.get("/api/v1/logs/statistics", params={"days": 7})
        assert s.status_code == 200
        stats = s.json()
        assert "error_count" in stats
        assert "token_trend" in stats
        assert "latency_trend" in stats
        assert stats["window_days"] == 7

    @pytest.mark.asyncio
    async def test_filter_by_event_prefix(self, client) -> None:
        reset_sink_for_tests()
        assert settings.LOG_DB_SINK is True
        emit_tool(
            LogEvent.TOOL_STARTED,
            tool_name="web_search",
            input_data={"q": "x"},
        )
        n = flush_agent_logs_sync(limit=20)
        assert n >= 1

        r = await client.get(
            "/api/v1/logs",
            params={"event": "tool.", "page_size": 10},
        )
        assert r.status_code == 200
        body = r.json()
        for item in body.get("items") or []:
            assert str(item.get("event", "")).startswith("tool.")
