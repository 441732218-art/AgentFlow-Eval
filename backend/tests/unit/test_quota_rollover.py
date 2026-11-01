# (c) 2026 AgentFlow-Eval
"""Billing period rollover unit tests.

E15g-1: UUID temp SQLite only; no fixed ./test_rollover.db; unlink only
files this fixture creates.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.billing.service import get_billing_service
from app.models.base import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest_asyncio.fixture
async def session():
    db_path = _BACKEND_ROOT / f"test_rollover_{uuid4().hex}.db"
    assert db_path.name != "test_rollover.db"
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
        async with factory() as s:
            yield s
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
async def test_rollover_creates_fresh_period(session):
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    await svc.subscribe(session, actor="dave", plan_code="free")
    bal = await svc._get_or_create_balance(session, "dave")
    bal.task_used = 10
    bal.token_used = 999
    await session.flush()

    # Same period → returns existing
    same = await svc.rollover_period(session, "dave", new_period=bal.period)
    assert same.id == bal.id
    assert same.task_used == 10

    # New period → zero counters
    new_p = "2099-01"
    fresh = await svc.rollover_period(session, "dave", new_period=new_p)
    assert fresh.period == new_p
    assert fresh.task_used == 0
    assert fresh.token_used == 0
    assert fresh.task_limit > 0
