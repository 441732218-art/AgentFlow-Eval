# (c) 2026 AgentFlow-Eval
"""AOLS logs API + DB sink (Phase 4)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.observability.aols.emit import emit_evaluation, emit_tool
from app.core.observability.aols.events import LogEvent
from app.core.observability.aols.sinks.db import (
    enqueue_agent_log,
    flush_agent_logs_sync,
    reset_sink_for_tests,
)
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_agent_logs.db"


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(TEST_DB, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    import app.config as cfg

    prev_url = cfg.settings.DATABASE_URL
    prev_sink = cfg.settings.LOG_DB_SINK
    cfg.settings.DATABASE_URL = TEST_DB
    cfg.settings.LOG_DB_SINK = True
    reset_sink_for_tests()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    cfg.settings.DATABASE_URL = prev_url
    cfg.settings.LOG_DB_SINK = prev_sink
    reset_sink_for_tests()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        import os

        os.remove("./test_agent_logs.db")
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
        from app.models.base import Base

        eng = create_engine(f"sqlite:///{db_path.as_posix()}")
        Base.metadata.create_all(eng, tables=[AgentLog.__table__])
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


class TestLogsAPI:
    @pytest.mark.asyncio
    async def test_list_and_statistics(self, client) -> None:
        reset_sink_for_tests()
        emit_evaluation(LogEvent.EVALUATION_STARTED, task_id="t-logs-1")
        emit_tool(
            LogEvent.TOOL_COMPLETED,
            tool_name="calculator",
            latency_ms=5,
            success=True,
            input_data={"x": 1},
            output_data="2",
        )
        flush_agent_logs_sync(limit=50)

        r = await client.get("/api/v1/logs", params={"page": 1, "page_size": 20})
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert body["page"] == 1

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
        emit_tool(
            LogEvent.TOOL_STARTED,
            tool_name="web_search",
            input_data={"q": "x"},
        )
        flush_agent_logs_sync(limit=20)

        r = await client.get(
            "/api/v1/logs",
            params={"event": "tool.", "page_size": 10},
        )
        assert r.status_code == 200
        body = r.json()
        for item in body.get("items") or []:
            assert str(item.get("event", "")).startswith("tool.")
