# (c) 2026 AgentFlow-Eval
"""Integration tests for Celery evaluation pipeline with mocked LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select

from app.core.celery_app.tasks import (
    evaluate_pipeline_task,
    run_full_evaluation,
    run_judge_evaluation,
    run_single_test_suite,
    _mark_task_failed,
)
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace
from app.core.celery_app.tests.conftest import (
    MOCK_AGENT_FAILED,
    MOCK_AGENT_SUCCESS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_suites(session, task_id: str) -> list[TestSuite]:
    result = await session.execute(select(TestSuite).where(TestSuite.task_id == task_id))
    return list(result.scalars().all())


async def _count_traces(session, suite_ids: list[str]) -> int:
    if not suite_ids:
        return 0
    result = await session.execute(
        select(func.count(Trace.id)).where(Trace.test_suite_id.in_(suite_ids))
    )
    return int(result.scalar() or 0)


async def _count_scores(session) -> int:
    result = await session.execute(select(func.count(MetricScore.id)))
    return int(result.scalar() or 0)


async def _reload_task(db_env, task_id: str) -> Task:
    async with db_env["factory"]() as session:
        row = await session.execute(select(Task).where(Task.id == task_id))
        return row.scalar_one()


# ---------------------------------------------------------------------------
# run_single_test_suite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_single_suite_success(db_session, sample_task, mock_llm):
    suites = await _get_suites(db_session, sample_task.id)
    suite = suites[0]

    result = run_single_test_suite(suite.id, sample_task.agent_config)

    assert result["status"] == "success"
    assert result["trace_id"] is not None
    assert result["total_tokens"] == 60
    assert result["final_answer"] == "The answer is 2"
    mock_llm["runner"].run.assert_awaited()

    # Trace persisted
    tr = await db_session.execute(select(Trace).where(Trace.id == result["trace_id"]))
    trace = tr.scalar_one()
    assert trace.user_query == suite.user_query
    assert len(trace.steps) == 2


@pytest.mark.asyncio
async def test_run_single_suite_agent_failed_status(db_session, sample_task, mock_llm):
    mock_llm["runner"].run = AsyncMock(return_value=dict(MOCK_AGENT_FAILED))
    suites = await _get_suites(db_session, sample_task.id)

    result = run_single_test_suite(suites[0].id, sample_task.agent_config)

    assert result["status"] == "failed"
    assert result["trace_id"] is not None  # still persisted
    assert "boom" in (result.get("error_message") or "")


@pytest.mark.asyncio
async def test_run_single_suite_missing_suite(db_session, mock_llm):
    result = run_single_test_suite("nonexistent-suite-id", {"model": "gpt-4o-mini"})
    assert result["status"] == "failed"
    assert result["trace_id"] is None
    assert "not found" in result["error_message"].lower()


@pytest.mark.asyncio
async def test_run_single_suite_runner_exception(db_session, sample_task, mock_llm):
    mock_llm["runner"].run = AsyncMock(side_effect=RuntimeError("LLM down"))
    suites = await _get_suites(db_session, sample_task.id)

    result = run_single_test_suite(suites[0].id, sample_task.agent_config)
    assert result["status"] == "failed"
    assert result["trace_id"] is None
    assert "LLM down" in result["error_message"]


# ---------------------------------------------------------------------------
# run_judge_evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_judge_success(db_session, sample_task, mock_llm):
    suites = await _get_suites(db_session, sample_task.id)
    suite_result = run_single_test_suite(suites[0].id, sample_task.agent_config)
    trace_id = suite_result["trace_id"]

    judge = run_judge_evaluation(
        trace_id,
        suites[0].expected_output,
        suites[0].expected_tools,
    )

    assert judge["trace_id"] == trace_id
    assert judge["total"] == 94.0
    assert "tool_accuracy" in judge["scores"]
    mock_llm["judge"].evaluate.assert_awaited()

    count = await _count_scores(db_session)
    assert count >= 3


@pytest.mark.asyncio
async def test_run_judge_missing_trace(db_session, mock_llm):
    result = run_judge_evaluation("missing-trace", "out", ["calculator"])
    assert result["total"] == 0.0
    assert "error_message" in result
    assert "not found" in result["error_message"].lower()


@pytest.mark.asyncio
async def test_run_judge_exception(db_session, sample_task, mock_llm):
    suites = await _get_suites(db_session, sample_task.id)
    suite_result = run_single_test_suite(suites[0].id, sample_task.agent_config)
    mock_llm["judge"].evaluate = AsyncMock(side_effect=ValueError("judge crash"))

    result = run_judge_evaluation(
        suite_result["trace_id"],
        "expected",
        ["calculator"],
    )
    assert result["total"] == 0.0
    assert "judge crash" in result["error_message"]


# ---------------------------------------------------------------------------
# Full pipeline / evaluate_pipeline_task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_pipeline_alias(db_session, sample_task, mock_llm):
    """evaluate_pipeline_task is an alias of run_full_evaluation."""
    assert evaluate_pipeline_task is run_full_evaluation


@pytest.mark.asyncio
async def test_full_pipeline_success(db_env, db_session, sample_task, mock_llm):
    result = run_full_evaluation(sample_task.id)

    assert result["task_id"] == sample_task.id
    assert result["status"] == "completed"
    assert result["total_suites"] == 2
    assert result["completed_suites"] == 2
    assert result["failed_suites"] == 0
    assert result["average_score"] == 94.0
    assert "tool_accuracy" in result["dimension_scores"]
    assert len(result["suites"]) == 2
    assert len(result["judgments"]) == 2

    task = await _reload_task(db_env, sample_task.id)
    assert task.status == TaskStatus.COMPLETED

    suites = await _get_suites(db_session, sample_task.id)
    n_traces = await _count_traces(db_session, [s.id for s in suites])
    assert n_traces == 2
    assert await _count_scores(db_session) >= 6


@pytest.mark.asyncio
async def test_full_pipeline_empty_suites(db_env, empty_task, mock_llm):
    result = run_full_evaluation(empty_task.id)
    assert result["status"] == "completed"
    assert result["total_suites"] == 0
    assert "No test suites" in result.get("message", "")

    task = await _reload_task(db_env, empty_task.id)
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_full_pipeline_missing_task(db_session, mock_llm):
    result = run_full_evaluation("does-not-exist-task")
    assert result["status"] == "failed"
    assert "not found" in result["error_message"].lower()


@pytest.mark.asyncio
async def test_full_pipeline_all_suites_fail(db_env, sample_task, mock_llm):
    mock_llm["runner"].run = AsyncMock(side_effect=RuntimeError("all fail"))

    result = run_full_evaluation(sample_task.id)

    assert result["status"] == "failed"
    assert result["completed_suites"] == 0
    assert result["failed_suites"] == 2

    task = await _reload_task(db_env, sample_task.id)
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_full_pipeline_partial_failure(db_env, sample_task, mock_llm):
    """First suite succeeds, second raises → partial with mixed results."""
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return dict(MOCK_AGENT_SUCCESS)
        raise RuntimeError("second suite boom")

    mock_llm["runner"].run = AsyncMock(side_effect=side_effect)

    result = run_full_evaluation(sample_task.id)

    assert result["total_suites"] == 2
    assert result["failed_suites"] >= 1
    if result["completed_suites"] >= 1:
        assert result["status"] == "partial"
        task = await _reload_task(db_env, sample_task.id)
        assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_full_pipeline_different_task_ids(db_env, mock_llm):
    """Two independent tasks both complete under mock LLM."""
    factory = db_env["factory"]
    async with factory() as session:
        t1 = Task(
            name="t1",
            description="",
            agent_config={"model": "gpt-4o-mini"},
            status=TaskStatus.QUEUED,
            created_by="a",
        )
        t2 = Task(
            name="t2",
            description="",
            agent_config={"model": "gpt-4o-mini"},
            status=TaskStatus.QUEUED,
            created_by="b",
        )
        session.add_all([t1, t2])
        await session.flush()
        for t in (t1, t2):
            session.add(
                TestSuite(
                    task_id=t.id,
                    user_query="q",
                    expected_output="a",
                    expected_tools=["calculator"],
                )
            )
        await session.commit()
        id1, id2 = t1.id, t2.id

    r1 = run_full_evaluation(id1)
    r2 = run_full_evaluation(id2)

    assert r1["task_id"] == id1 and r1["status"] == "completed"
    assert r2["task_id"] == id2 and r2["status"] == "completed"
    assert r1["task_id"] != r2["task_id"]


@pytest.mark.asyncio
async def test_mark_task_failed(db_env, sample_task):
    await _mark_task_failed(sample_task.id, "forced")
    task = await _reload_task(db_env, sample_task.id)
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_mark_task_failed_missing(db_session):
    # Should not raise
    await _mark_task_failed("no-such-id", "x")


@pytest.mark.asyncio
async def test_status_machine_queued_to_completed(db_env, sample_task, mock_llm):
    assert sample_task.status == TaskStatus.QUEUED
    run_full_evaluation(sample_task.id)
    task = await _reload_task(db_env, sample_task.id)
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_judge_accepts_object_result(db_session, sample_task, mock_llm):
    """Judge result as object with attributes still works."""
    suites = await _get_suites(db_session, sample_task.id)
    suite_result = run_single_test_suite(suites[0].id, sample_task.agent_config)

    obj = MagicMock()
    obj.scores = {"tool_accuracy": 40.0, "answer_correctness": 40.0, "reasoning_coherence": 20.0}
    obj.total = 100.0
    obj.reason = "object-style"
    obj.token_cost = 5
    mock_llm["judge"].evaluate = AsyncMock(return_value=obj)

    j = run_judge_evaluation(suite_result["trace_id"], "out", [])
    assert j["total"] == 100.0
    assert j["token_cost"] == 5
