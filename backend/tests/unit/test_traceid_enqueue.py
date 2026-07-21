# (c) 2026 AgentFlow-Eval
"""TraceID is forwarded on task enqueue kwargs."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.ports.task_queue import EnqueueResult
from app.core.observability.tracing import set_trace_id


@pytest.mark.asyncio
async def test_execute_passes_trace_id_kwarg():
    """Patch queue and assert enqueue kwargs contain _trace_id."""
    import os

    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from app.core.dependencies import get_db
    from app.main import app
    from app.models.base import Base

    db = "sqlite+aiosqlite:///./test_trace_enq.db"
    engine = create_async_engine(db, echo=False)
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
                        # middleware will set its own request id; we assert kwargs present
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
        # kwargs may be under kwargs key of enqueue()
        enq_kwargs = kwargs.get("kwargs") or {}
        assert enq_kwargs.get("_trace_id") == "fixed-trace-id-001"
    finally:
        app.dependency_overrides.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
        try:
            os.remove("./test_trace_enq.db")
        except OSError:
            pass
