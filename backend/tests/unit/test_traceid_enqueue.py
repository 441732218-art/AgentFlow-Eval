# (c) 2026 AgentFlow-Eval
"""TraceID is forwarded on task enqueue kwargs.

E15d-1: unique UUID temp SQLite; reversible get_db override; deps.engine /
factory rebound; AOLS LOG_DB_SINK disabled. No fixed ./test_trace_enq.db
and no dependency_overrides.clear().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.ports.task_queue import EnqueueResult
from app.core.observability.tracing import set_trace_id

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.asyncio
async def test_execute_passes_trace_id_kwarg():
    """Patch queue and assert enqueue kwargs contain _trace_id."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from app.config import settings
    from app.core import dependencies as deps
    from app.core.dependencies import get_db
    from app.core.observability.aols.sinks import db as aols_db_sink
    from app.main import app
    from app.models.base import Base

    db_path = _BACKEND_ROOT / f"test_trace_enq_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_trace_enq.db"

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
    set_trace_id("fixed-trace-id-001")

    mock_q = MagicMock()
    mock_q.enqueue.return_value = EnqueueResult(
        task_id="j1", backend="eager", eager=True
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.config.settings.AUTH_ENABLED", False):
                with patch("app.config.settings.RBAC_ENABLED", False):
                    with patch("app.core.profiles.get_task_queue", return_value=mock_q):
                        cr = await client.post(
                            "/api/v1/tasks",
                            json={"name": "t", "description": "", "agent_config": {}},
                            headers={"X-Request-ID": "fixed-trace-id-001"},
                        )
                        assert cr.status_code == 201, cr.text
                        tid = cr.json()["id"]
                        ex = await client.post(
                            f"/api/v1/tasks/{tid}/execute",
                            headers={"X-Request-ID": "fixed-trace-id-001"},
                        )
                        assert ex.status_code == 200, ex.text
        assert mock_q.enqueue.called
        kwargs = mock_q.enqueue.call_args.kwargs
        enq_kwargs = kwargs.get("kwargs") or {}
        assert enq_kwargs.get("_trace_id") == "fixed-trace-id-001"
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
