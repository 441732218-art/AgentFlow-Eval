# (c) 2026 AgentFlow-Eval
"""Tests for optimized DB query helpers and model indexes."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db.queries import batch_suite_counts, tasks_with_suite_counts
from app.models.base import Base
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite

TEST_DB = "sqlite+aiosqlite:///./test_db_queries.db"


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
        os.remove("./test_db_queries.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_batch_suite_counts(session: AsyncSession):
    t1 = Task(name="a", description="", agent_config={}, status=TaskStatus.CREATED)
    t2 = Task(name="b", description="", agent_config={}, status=TaskStatus.CREATED)
    t3 = Task(name="c", description="", agent_config={}, status=TaskStatus.CREATED)
    session.add_all([t1, t2, t3])
    await session.flush()
    session.add_all(
        [
            TestSuite(task_id=t1.id, user_query="q1", expected_output=""),
            TestSuite(task_id=t1.id, user_query="q2", expected_output=""),
            TestSuite(task_id=t2.id, user_query="q3", expected_output=""),
        ]
    )
    await session.commit()

    counts = await batch_suite_counts(session, [t1.id, t2.id, t3.id])
    assert counts[t1.id] == 2
    assert counts[t2.id] == 1
    assert t3.id not in counts  # zero suites → omitted; callers use .get(..., 0)

    pairs = await tasks_with_suite_counts(session, [t1, t2, t3])
    assert pairs[0][1] == 2
    assert pairs[1][1] == 1
    assert pairs[2][1] == 0


@pytest.mark.asyncio
async def test_batch_suite_counts_empty(session: AsyncSession):
    assert await batch_suite_counts(session, []) == {}


def test_task_model_has_list_indexes():
    """ORM metadata declares composite indexes used by list_tasks."""
    table = Task.__table__
    names = {ix.name for ix in table.indexes}
    assert "ix_tasks_owner_archived_created" in names
    assert "ix_tasks_status_created" in names


def test_trace_and_score_indexes():
    from app.models.metric_score import MetricScore
    from app.models.trace import Trace

    assert any(
        ix.name == "ix_traces_suite_created" for ix in Trace.__table__.indexes
    )
    assert any(
        ix.name == "ix_metric_scores_trace_metric"
        for ix in MetricScore.__table__.indexes
    )


def test_migration_index_list_covers_hot_paths():
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "007_performance_indexes.py"
    )
    spec = importlib.util.spec_from_file_location("m007", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    names = {row[0] for row in mod._INDEXES}
    assert "ix_tasks_owner_archived_created" in names
    assert "ix_traces_suite_created" in names
    assert "ix_metric_scores_trace_metric" in names
    assert "ix_audit_logs_created_at" in names
