# (c) 2026 AgentFlow-Eval
"""Fixtures for Celery evaluation pipeline integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app.celery import celery_app
from app.models.base import Base
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite

# Isolated SQLite DB for celery pipeline tests
CELERY_TEST_DB = "sqlite+aiosqlite:///./test_celery_pipeline.db"

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


@pytest.fixture(scope="module", autouse=True)
def celery_eager_mode() -> Generator[None, None, None]:
    """Force Celery tasks to run synchronously in-process."""
    prev_eager = celery_app.conf.task_always_eager
    prev_prop = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
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
    """Provide test DB engine + session factory wired into Celery tasks."""
    engine = create_async_engine(CELERY_TEST_DB, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import app.core.celery_app.tasks as tasks_mod
    import app.core.dependencies as deps

    prev_factory = deps.async_session_factory
    prev_tasks_factory = tasks_mod.async_session_factory
    deps.async_session_factory = factory
    tasks_mod.async_session_factory = factory

    yield {"engine": engine, "factory": factory}

    deps.async_session_factory = prev_factory
    tasks_mod.async_session_factory = prev_tasks_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_celery_pipeline.db")
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
        # Detach id for use after session closes
        task_id = task.id
        agent_config = dict(task.agent_config or {})

    # Return a lightweight namespace-like object
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
