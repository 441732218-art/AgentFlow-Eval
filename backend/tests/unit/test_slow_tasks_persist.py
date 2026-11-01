# (c) 2026 AgentFlow-Eval
"""Slow-task memory buffer + durable listing.

E15g-1: UUID temp SQLite; monkeypatch async_session_factory so
list_slow_tasks_db cannot touch agentflow_eval.db; no fixed
./test_slow_tasks.db; unlink only files this fixture creates.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.observability.slow_tasks import (
    clear_slow_tasks,
    list_slow_tasks,
    list_slow_tasks_db,
    record_slow_task,
)
from app.models.base import Base
from app.models.slow_task import SlowTaskEvent

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def _mem():
    clear_slow_tasks()
    yield
    clear_slow_tasks()


def test_record_under_threshold_skipped():
    assert (
        record_slow_task(
            stage="agent",
            duration_sec=1.0,
            threshold_sec=30.0,
            persist=False,
        )
        is False
    )
    assert list_slow_tasks() == []


def test_record_to_memory_with_actor_trace():
    ok = record_slow_task(
        stage="judge",
        duration_sec=99.0,
        threshold_sec=30.0,
        ref_id="t1",
        status="ok",
        actor="alice",
        trace_id="trace-xyz",
        persist=False,
    )
    assert ok is True
    items = list_slow_tasks()
    assert len(items) == 1
    assert items[0]["actor"] == "alice"
    assert items[0]["trace_id"] == "trace-xyz"
    assert items[0]["stage"] == "judge"


@pytest_asyncio.fixture
async def db_engine(monkeypatch):
    db_path = _BACKEND_ROOT / f"test_slow_tasks_{uuid4().hex}.db"
    assert db_path.name != "test_slow_tasks.db"
    assert "agentflow_eval.db" not in db_path.name
    owned = not db_path.exists()
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    engine = create_async_engine(test_db_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        # list_slow_tasks_db imports async_session_factory from dependencies
        monkeypatch.setattr(
            "app.core.dependencies.async_session_factory", factory
        )
        yield factory
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
        if owned and db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass


@pytest.mark.asyncio
async def test_persist_and_list_db(db_engine):
    # Direct insert via model to avoid asyncio.run nesting issues in record
    async with db_engine() as session:
        session.add(
            SlowTaskEvent(
                id="slow-1",
                stage="agent",
                duration_sec=45.5,
                threshold_sec=30.0,
                ref_id="r1",
                status="ok",
                trace_id="tr-1",
                actor="bob",
                extra={"runner": "openai"},
            )
        )
        await session.commit()

    items = await list_slow_tasks_db(limit=10)
    assert any(i["trace_id"] == "tr-1" and i["actor"] == "bob" for i in items)
