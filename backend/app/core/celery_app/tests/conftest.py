# (c) 2026 AgentFlow-Eval
"""Fixtures for Celery evaluation pipeline integration tests.

E15g-4B: UUID temp SQLite (anchored under backend/); rebind deps.engine,
deps.async_session_factory, and tasks_mod.async_session_factory (tasks.py
binds factory at import); LOG_DB_SINK stays True with DATABASE_URL -> UUID
so flush_agent_logs_sync persists into the isolated DB; AOLS queue
snapshotted/restored; no fixed ./test_celery_pipeline.db; unlink only
owned UUID files.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.core.celery_app.celery import celery_app
from app.models.base import Base
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite

# backend/app/core/celery_app/tests/conftest.py -> parents[4] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[4]
_REPO_ROOT = Path(__file__).resolve().parents[5]
_AOLS_EVIDENCE = _REPO_ROOT / "_verify-logs" / "E15g4-aols-uuid-writes.txt"

MOCK_AGENT_SUCCESS: dict[str, Any] = {
    "steps": [
        {
            "iteration": 0,
            "thought": "I should calculate",
            "action": "calculator",
            "action_input": '{"expression": "1+1"}',
            "observation": "Result: 2",
            "tokens": 40,
        },
        {
            "iteration": 1,
            "thought": "Done",
            "action": "final_answer",
            "action_input": "The answer is 2",
            "observation": "",
            "tokens": 20,
        },
    ],
    "total_tokens": 60,
    "iterations": 2,
    "final_answer": "The answer is 2",
    "status": "success",
    "error_message": "",
    "response_time_ms": 120,
}

MOCK_AGENT_FAILED: dict[str, Any] = {
    "steps": [
        {
            "iteration": 0,
            "thought": "error",
            "action": "",
            "action_input": "",
            "observation": "[Error: boom]",
            "tokens": 10,
        }
    ],
    "total_tokens": 10,
    "iterations": 1,
    "final_answer": None,
    "status": "failed",
    "error_message": "boom",
    "response_time_ms": 50,
}

MOCK_JUDGE_RESULT: dict[str, Any] = {
    "scores": {
        "tool_accuracy": 40.0,
        "answer_correctness": 36.0,
        "reasoning_coherence": 18.0,
    },
    "total": 94.0,
    "reason": "[Rule-based] Mock judge OK",
    "token_cost": 0,
    "mode": "rule_only",
}


def _count_agent_logs_sync(db_path: Path) -> int:
    """Read agent_logs count from UUID sqlite via sync engine (AOLS path)."""
    from app.models.agent_log import AgentLog

    sync_url = f"sqlite:///{db_path.as_posix()}"
    eng = create_engine(sync_url)
    try:
        with Session(eng) as session:
            return int(session.scalar(select(func.count(AgentLog.id))) or 0)
    except Exception:
        return 0
    finally:
        eng.dispose()


def _record_aols_evidence(db_path: Path, flushed: int, rows: int) -> None:
    try:
        _AOLS_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        with _AOLS_EVIDENCE.open("a", encoding="utf-8") as fh:
            fh.write(
                f"db={db_path.name} flushed={flushed} agent_log_rows={rows} "
                f"LOG_DB_SINK={bool(getattr(settings, 'LOG_DB_SINK', False))} "
                f"url_is_uuid={'test_celery_pipeline_' in (settings.DATABASE_URL or '')}\n"
            )
    except OSError:
        pass


@pytest.fixture(scope="module", autouse=True)
def celery_eager_mode() -> Generator[None, None, None]:
    """Force Celery tasks to run synchronously in-process (no real broker)."""
    prev_eager = celery_app.conf.task_always_eager
    prev_prop = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True
    yield
    celery_app.conf.task_always_eager = prev_eager
    celery_app.conf.task_eager_propagates = prev_prop


@pytest.fixture
def mock_llm() -> Generator[dict[str, Any], None, None]:
    """Mock ReAct agent runner + LLM judge factories.

    Returns a dict with handles so tests can change side_effects mid-test:
      mock_llm["runner"].run.return_value = ...
      mock_llm["judge"].evaluate.return_value = ...
    """
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=dict(MOCK_AGENT_SUCCESS))

    mock_judge = MagicMock()
    mock_judge.evaluate = AsyncMock(return_value=dict(MOCK_JUDGE_RESULT))

    with (
        patch(
            "app.core.celery_app.tasks.build_agent_runner",
            return_value=mock_runner,
        ) as p_runner,
        patch(
            "app.core.celery_app.tasks.build_llm_judge",
            return_value=mock_judge,
        ) as p_judge,
    ):
        yield {
            "runner": mock_runner,
            "judge": mock_judge,
            "patch_runner": p_runner,
            "patch_judge": p_judge,
            "agent_success": MOCK_AGENT_SUCCESS,
            "agent_failed": MOCK_AGENT_FAILED,
            "judge_result": MOCK_JUDGE_RESULT,
        }


@pytest_asyncio.fixture
async def db_env() -> AsyncGenerator[dict[str, Any], None]:
    """UUID SQLite + dual factory/engine rebind + AOLS URL isolation."""
    import app.models  # noqa: F401 — register AgentLog etc. on Base.metadata
    import app.core.celery_app.tasks as tasks_mod
    import app.core.dependencies as deps
    from app.core.observability.aols.sinks import db as aols_db_sink
    from app.core.observability.aols.sinks.db import flush_agent_logs_sync

    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True

    db_path = _BACKEND_ROOT / f"test_celery_pipeline_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert db_path.name != "test_celery_pipeline.db"
    assert "agentflow_eval.db" not in test_db_url
    assert settings.DATABASE_URL != test_db_url
    owned = not db_path.exists()

    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_tasks_factory = tasks_mod.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))

    # Snapshot shared AOLS queue; this fixture exclusively owns the queue
    # for the duration of the test (restore foreign rows on teardown).
    with aols_db_sink._lock:
        prev_queue = list(aols_db_sink._queue)
        aols_db_sink._queue.clear()

    deps.engine = engine
    deps.async_session_factory = factory
    tasks_mod.async_session_factory = factory
    # flush_agent_logs_sync builds a fresh sync engine from settings.DATABASE_URL
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = True

    try:
        yield {
            "engine": engine,
            "factory": factory,
            "db_path": db_path,
            "db_url": test_db_url,
        }
    finally:
        # 1-2. Eager tasks already completed (sync/.result); drain AOLS to UUID
        flushed = 0
        try:
            flushed = int(flush_agent_logs_sync(limit=500) or 0)
        except Exception:
            flushed = 0

        rows = _count_agent_logs_sync(db_path)
        _record_aols_evidence(db_path, flushed, rows)
        if flushed > 0:
            assert rows >= 1, "AOLS flush reported writes but UUID agent_logs empty"
            assert db_path.exists()

        # Drop any remaining rows owned by this fixture period
        with aols_db_sink._lock:
            aols_db_sink._queue.clear()
            aols_db_sink._queue.extend(prev_queue)

        # 4-5. Restore settings / bindings before drop/dispose
        settings.LOG_DB_SINK = prev_sink
        settings.DATABASE_URL = prev_db_url
        deps.engine = prev_engine
        deps.async_session_factory = prev_factory
        tasks_mod.async_session_factory = prev_tasks_factory

        # 6-7. drop + dispose owned engine only
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
        await engine.dispose()

        # 8. Unlink only owned UUID file
        if owned and db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass


@pytest_asyncio.fixture
async def db_session(db_env: dict[str, Any]) -> AsyncGenerator[AsyncSession, None]:
    factory = db_env["factory"]
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def sample_task(db_env: dict[str, Any]) -> Task:
    """Create a Task with two test suites for pipeline tests."""
    factory = db_env["factory"]
    async with factory() as session:
        task = Task(
            name="celery-pipeline-task",
            description="integration",
            agent_config={"model": "gpt-4o-mini", "max_iterations": 3},
            status=TaskStatus.QUEUED,
            created_by="tester",
        )
        session.add(task)
        await session.flush()

        suites = [
            TestSuite(
                task_id=task.id,
                user_query="What is 1+1?",
                expected_output="2",
                expected_tools=["calculator"],
            ),
            TestSuite(
                task_id=task.id,
                user_query="What is 2+2?",
                expected_output="4",
                expected_tools=["calculator"],
            ),
        ]
        for s in suites:
            session.add(s)
        await session.commit()
        await session.refresh(task)
        task_id = task.id
        agent_config = dict(task.agent_config or {})

    task_ref = MagicMock()
    task_ref.id = task_id
    task_ref.agent_config = agent_config
    task_ref.status = TaskStatus.QUEUED
    return task_ref


@pytest_asyncio.fixture
async def empty_task(db_env: dict[str, Any]) -> Task:
    """Task with zero suites."""
    factory = db_env["factory"]
    async with factory() as session:
        task = Task(
            name="empty-task",
            description="",
            agent_config={"model": "gpt-4o-mini"},
            status=TaskStatus.QUEUED,
            created_by="tester",
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id

    task_ref = MagicMock()
    task_ref.id = task_id
    task_ref.agent_config = {"model": "gpt-4o-mini"}
    task_ref.status = TaskStatus.QUEUED
    return task_ref
