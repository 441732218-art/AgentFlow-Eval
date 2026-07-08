# (c) 2026 AgentFlow-Eval
"""Test fixtures for AgentFlow-Eval E2E tests."""

import asyncio, os
import pytest, pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

TEST_DB_URL = "sqlite+aiosqlite:///./test_e2e.db"
ENGINE = create_async_engine(TEST_DB_URL, echo=False)

@pytest_asyncio.fixture(scope="class")
async def db_session():
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(ENGINE, class_=AsyncSession)()
    async def _override():
        yield session
    app.dependency_overrides[get_db] = _override
    yield session
    app.dependency_overrides.clear()
    await session.close()
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    try:
        os.remove("./test_e2e.db")
    except OSError:
        pass

@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
