# (c) 2026 AgentFlow-Eval
"""Test fixtures for AgentFlow-Eval E2E tests.

E15b: no module-level fixed `./test_e2e.db` engine. Each TestEndToEnd class
run gets a unique temporary SQLite file, get_db override, and deps/AOLS
isolation so /health cannot open agentflow_eval.db.
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
from app.main import app
from app.models.base import Base


@pytest_asyncio.fixture(scope="class")
async def db_session(tmp_path_factory):
    """Class-scoped isolated DB for E2E (shared task_id across methods)."""
    from app.core.observability.aols.sinks import db as aols_db_sink

    db_dir = Path(tmp_path_factory.mktemp("e2e_db"))
    db_path = db_dir / f"test_e2e_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    assert "agentflow_eval.db" not in test_db_url
    assert "test_tasks_unit.db" not in test_db_url
    assert "test_e2e.db" != db_path.name
    assert settings.DATABASE_URL != test_db_url

    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()

    async def _override():
        yield session

    had_get_db = get_db in app.dependency_overrides
    prev_get_db = app.dependency_overrides.get(get_db)
    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))

    # /health probes deps.engine; AOLS flush reads settings.DATABASE_URL
    deps.engine = engine
    deps.async_session_factory = factory
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = False
    app.dependency_overrides[get_db] = _override

    try:
        yield session
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
        await session.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
        try:
            if db_path.exists():
                db_path.unlink()
        except OSError:
            pass


@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
