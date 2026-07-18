# (c) 2026 AgentFlow-Eval
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.billing.service import get_billing_service, period_key
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_rollover.db"


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
        os.remove("./test_rollover.db")
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
