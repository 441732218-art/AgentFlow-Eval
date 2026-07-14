# (c) 2026 AgentFlow-Eval
"""Celery async evaluation pipeline.

Architecture:
  Connects OpenAIReActRunner and LLMJudge into an automated pipeline:

    run_full_evaluation / evaluate_pipeline_task(task_id)
         │
         ├── 1. Load Task + TestSuites from DB
         ├── 2. Update status QUEUED → RUNNING
         ├── 3. For each TestSuite (parallel via Celery group):
         │       └── run_single_test_suite
         │            ├── OpenAIReActRunner.run(query, tools)
         │            └── Persist Trace to DB
         ├── 4. For each Trace (parallel via Celery group):
         │       └── run_judge_evaluation
         │            ├── LLMJudge.evaluate(trace_steps, expected)
         │            └── Persist MetricScore to DB
         ├── 5. Aggregate results
         └── 6. Update status to "completed" or "failed"
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from celery import group
from sqlalchemy import select

from app.core.celery_app.celery import celery_app
from app.core.dependencies import async_session_factory
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace, TraceStatus

logger = logging.getLogger(__name__)


def _emit_status(task: Task, status: TaskStatus | str, prev: str | None = None) -> None:
    """Best-effort live event for WebSocket clients."""
    try:
        from app.core.events import publish_task_status

        st = status.value if isinstance(status, TaskStatus) else str(status)
        publish_task_status(
            task.id,
            task.name or task.id,
            st,
            prev_status=prev,
            actor=getattr(task, "created_by", None),
        )
    except Exception as exc:
        logger.debug("publish_task_status skipped: %s", exc)


# ---------------------------------------------------------------------------
# Test seams — patch these in unit/integration tests
# ---------------------------------------------------------------------------


def build_agent_runner(agent_config: dict[str, Any] | None = None):
    """Factory for OpenAIReActRunner (patchable in tests)."""
    from app.config import settings as app_settings
    from app.core.agent_runner.openai_runner import OpenAIReActRunner

    cfg = agent_config or {}
    return OpenAIReActRunner(
        api_key=app_settings.OPENAI_API_KEY or None,
        base_url=app_settings.OPENAI_BASE_URL or None,
        model=cfg.get("model", "gpt-4o-mini"),
        max_iterations=cfg.get("max_iterations", 5),
    )


def build_llm_judge():
    """Factory for LLMJudge (patchable in tests)."""
    from app.core.judge_engine.llm_judge import LLMJudge

    return LLMJudge()


def _run_async(async_factory):
    """Run an async factory (zero-arg → coroutine) from a sync Celery task.

    Safe when called from a worker thread *or* from pytest-asyncio (nested loop):
    if a loop is already running, the coroutine is executed in a fresh thread.
    """
    import asyncio
    import concurrent.futures

    def _runner():
        return asyncio.run(async_factory())

    try:
        asyncio.get_running_loop()
        nested = True
    except RuntimeError:
        nested = False

    if nested:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_runner).result()
    return _runner()


# ---------------------------------------------------------------------------
# Sub-task 1: Execute a single test suite via OpenAIReActRunner
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=320,
    acks_late=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
)
def run_single_test_suite(self, test_suite_id: str, agent_config: dict) -> dict:
    """Execute one test case using OpenAIReActRunner and persist the Trace."""
    logger.info("[Suite %s] Starting execution", test_suite_id)

    async def _execute():
        async with async_session_factory() as session:
            result = await session.execute(
                select(TestSuite).where(TestSuite.id == test_suite_id)
            )
            suite = result.scalar_one_or_none()
            if not suite:
                raise ValueError(f"TestSuite not found: {test_suite_id}")

            from app.core.agent_runner.tool_sandbox import resolve_tools_for_suite

            runner = build_agent_runner(agent_config or {})
            tools = resolve_tools_for_suite(suite.expected_tools)

            agent_result = await runner.run(
                query=suite.user_query,
                tools=tools,
            )

            status_map = {
                "success": TraceStatus.SUCCESS,
                "max_iterations_reached": TraceStatus.FAILED,
                "failed": TraceStatus.FAILED,
            }
            trace_status = status_map.get(
                agent_result.get("status", ""), TraceStatus.FAILED
            )

            trace = Trace(
                test_suite_id=test_suite_id,
                user_query=suite.user_query,
                steps=agent_result.get("steps", []),
                total_tokens=agent_result.get("total_tokens", 0),
                response_time_ms=agent_result.get("response_time_ms", 0),
                status=trace_status,
            )
            session.add(trace)
            await session.commit()
            await session.refresh(trace)

            return {
                "trace_id": trace.id,
                "status": trace.status.value,
                "total_tokens": trace.total_tokens,
                "response_time_ms": trace.response_time_ms,
                "step_count": len(trace.steps),
                "iterations": agent_result.get("iterations", 0),
                "final_answer": agent_result.get("final_answer", ""),
                "error_message": agent_result.get("error_message", ""),
            }

    try:
        result = _run_async(_execute)
        logger.info(
            "[Suite %s] Completed: trace=%s status=%s tokens=%d",
            test_suite_id,
            result.get("trace_id"),
            result.get("status"),
            result.get("total_tokens", 0),
        )
        return result
    except Exception as exc:
        logger.exception("[Suite %s] Execution failed: %s", test_suite_id, exc)
        # Retry on transient network errors if retries remain
        return {
            "trace_id": None,
            "status": "failed",
            "total_tokens": 0,
            "response_time_ms": 0,
            "step_count": 0,
            "iterations": 0,
            "final_answer": "",
            "error_message": str(exc),
        }


# ---------------------------------------------------------------------------
# Sub-task 2: Judge a single trace via LLMJudge
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=320,
    acks_late=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
)
def run_judge_evaluation(
    self, trace_id: str, expected_output: str, expected_tools: list
) -> dict:
    """Score one Trace using LLMJudge and persist the MetricScores."""
    logger.info("[Judge %s] Starting evaluation", trace_id)

    async def _judge():
        async with async_session_factory() as session:
            result = await session.execute(select(Trace).where(Trace.id == trace_id))
            trace = result.scalar_one_or_none()
            if not trace:
                raise ValueError(f"Trace not found: {trace_id}")

            judge = build_llm_judge()
            judge_result = await judge.evaluate(
                trace_steps=trace.steps,
                expected_output=expected_output,
                expected_tools=expected_tools or [],
            )

            # Support both dict and object-style results
            if isinstance(judge_result, dict):
                scores = judge_result.get("scores", {})
                total = float(judge_result.get("total", 0.0))
                reason = judge_result.get("reason", "")
                token_cost = int(judge_result.get("token_cost", 0) or 0)
            else:
                scores = getattr(judge_result, "scores", {}) or {}
                total = float(getattr(judge_result, "total", 0.0) or 0.0)
                reason = getattr(judge_result, "reason", "") or ""
                token_cost = int(getattr(judge_result, "token_cost", 0) or 0)

            for metric_name, score in scores.items():
                ms = MetricScore(
                    trace_id=trace_id,
                    metric_name=metric_name,
                    score=float(score),
                    reason=reason,
                    extra_metadata={"token_cost": token_cost},
                )
                session.add(ms)

            await session.commit()

            return {
                "trace_id": trace_id,
                "scores": scores,
                "total": total,
                "reason": reason,
                "token_cost": token_cost,
            }

    try:
        result = _run_async(_judge)
        logger.info(
            "[Judge %s] Completed: total=%.1f token_cost=%d",
            trace_id,
            result.get("total", 0),
            result.get("token_cost", 0),
        )
        return result
    except Exception as exc:
        logger.exception("[Judge %s] Evaluation failed: %s", trace_id, exc)
        return {
            "trace_id": trace_id,
            "scores": {},
            "total": 0.0,
            "reason": f"Evaluation failed: {exc}",
            "token_cost": 0,
            "error_message": str(exc),
        }


# ---------------------------------------------------------------------------
# Orchestrator: Full evaluation pipeline
# ---------------------------------------------------------------------------


@celery_app.task(bind=True)
def run_full_evaluation(self, task_id: str) -> dict:
    """Orchestrate the full evaluation pipeline for a task.

    Pipeline:
      1. Load task + test suites from DB, set status to running
      2. Execute all suites in parallel (Celery group)
      3. Judge all traces in parallel
      4. Aggregate results
      5. Persist final status
    """
    logger.info("[Task %s] Full evaluation started", task_id)

    async def _orchestrate():
        async with async_session_factory() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                raise ValueError(f"Task not found: {task_id}")

            # Status machine: allow QUEUED or CREATED → RUNNING
            prev = task.status.value
            if task.status in (TaskStatus.CREATED, TaskStatus.QUEUED):
                task.status = TaskStatus.RUNNING
            else:
                # Already running/judging — continue idempotently
                if task.status not in (
                    TaskStatus.RUNNING,
                    TaskStatus.JUDGING,
                ):
                    task.status = TaskStatus.RUNNING
            await session.commit()
            if prev != task.status.value:
                _emit_status(task, task.status, prev)

            suite_result = await session.execute(
                select(TestSuite).where(TestSuite.task_id == task_id)
            )
            suites = list(suite_result.scalars().all())

            if not suites:
                prev = task.status.value
                task.status = TaskStatus.COMPLETED
                await session.commit()
                _emit_status(task, task.status, prev)
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "total_suites": 0,
                    "completed_suites": 0,
                    "failed_suites": 0,
                    "average_score": 0.0,
                    "message": "No test suites found.",
                }

            total = len(suites)
            try:
                self.update_state(
                    state="RUNNING",
                    meta={
                        "task_id": task_id,
                        "phase": "executing",
                        "total_suites": total,
                        "completed": 0,
                    },
                )
            except Exception:
                # Eager mode / tests may not support update_state fully
                pass

            # Execute suites (group with eager mode runs inline)
            suite_jobs = [
                run_single_test_suite.s(suite.id, task.agent_config or {})
                for suite in suites
            ]
            suite_group = group(suite_jobs)
            suite_async = suite_group.apply_async()
            suite_results = suite_async.get(disable_sync_subtasks=False)

            # Normalize results list
            if not isinstance(suite_results, (list, tuple)):
                suite_results = [suite_results]

            successful_suites = [
                r
                for r in suite_results
                if r and r.get("trace_id") and r.get("status") != "failed"
            ]
            failed_suites = [
                r
                for r in suite_results
                if not r or not r.get("trace_id") or r.get("status") == "failed"
            ]

            try:
                self.update_state(
                    state="RUNNING",
                    meta={
                        "task_id": task_id,
                        "phase": "judging",
                        "total_suites": total,
                        "completed_suites": len(successful_suites),
                        "failed_suites": len(failed_suites),
                    },
                )
            except Exception:
                pass

            prev = task.status.value
            task.status = TaskStatus.JUDGING
            await session.commit()
            _emit_status(task, task.status, prev)

            judge_jobs = []
            for suite, s_result in zip(suites, suite_results):
                if not s_result:
                    continue
                tid = s_result.get("trace_id")
                if tid:
                    judge_jobs.append(
                        run_judge_evaluation.s(
                            tid,
                            suite.expected_output or "",
                            suite.expected_tools or [],
                        )
                    )

            if judge_jobs:
                judge_async = group(judge_jobs).apply_async()
                judge_results = judge_async.get(disable_sync_subtasks=False)
                if not isinstance(judge_results, (list, tuple)):
                    judge_results = [judge_results]
            else:
                judge_results = []

            total_score = 0.0
            score_count = 0
            dimension_scores: dict[str, list[float]] = {}
            total_tokens = 0
            total_time_ms = 0

            for jr in judge_results:
                if not jr:
                    continue
                total_score += float(jr.get("total", 0.0) or 0.0)
                score_count += 1
                total_tokens += int(jr.get("token_cost", 0) or 0)
                for dim, val in (jr.get("scores") or {}).items():
                    dimension_scores.setdefault(dim, []).append(float(val))

            for s_result in suite_results:
                if not s_result:
                    continue
                total_tokens += int(s_result.get("total_tokens", 0) or 0)
                total_time_ms += int(s_result.get("response_time_ms", 0) or 0)

            avg_score = round(total_score / score_count, 1) if score_count else 0.0
            avg_dim_scores = (
                {
                    dim: round(sum(vals) / len(vals), 1)
                    for dim, vals in dimension_scores.items()
                }
                if dimension_scores
                else {}
            )

            overall_status = "completed"
            if failed_suites and not successful_suites:
                overall_status = "failed"
            elif failed_suites:
                overall_status = "partial"

            prev = task.status.value
            task.status = (
                TaskStatus.FAILED
                if overall_status == "failed"
                else TaskStatus.COMPLETED
            )
            await session.commit()
            _emit_status(task, task.status, prev)

            try:
                self.update_state(
                    state=overall_status.upper(),
                    meta={
                        "task_id": task_id,
                        "phase": "done",
                        "total_suites": total,
                        "completed_suites": len(successful_suites),
                        "failed_suites": len(failed_suites),
                        "average_score": avg_score,
                    },
                )
            except Exception:
                pass

            return {
                "task_id": task_id,
                "status": overall_status,
                "total_suites": total,
                "completed_suites": len(successful_suites),
                "failed_suites": len(failed_suites),
                "average_score": avg_score,
                "dimension_scores": avg_dim_scores,
                "total_tokens": total_tokens,
                "total_time_ms": total_time_ms,
                "suites": list(suite_results),
                "judgments": list(judge_results),
            }

    try:
        result = _run_async(_orchestrate)
        logger.info(
            "[Task %s] Completed: status=%s suites=%d/%d score=%.1f",
            task_id,
            result.get("status"),
            result.get("completed_suites", 0),
            result.get("total_suites", 0),
            result.get("average_score", 0.0),
        )
        return result
    except Exception as exc:
        logger.exception("[Task %s] Orchestration failed: %s", task_id, exc)
        _run_async(lambda: _mark_task_failed(task_id, str(exc)))
        return {
            "task_id": task_id,
            "status": "failed",
            "error_message": str(exc),
            "total_suites": 0,
            "completed_suites": 0,
            "failed_suites": 0,
            "average_score": 0.0,
        }


# Public alias used by docs / external callers
evaluate_pipeline_task = run_full_evaluation


async def _mark_task_failed(task_id: str, error: str) -> None:
    """Mark a task as failed in the database."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                prev = task.status.value
                task.status = TaskStatus.FAILED
                await session.commit()
                _emit_status(task, task.status, prev)
                logger.info("[Task %s] marked FAILED: %s", task_id, error)
    except Exception as exc:
        logger.error("Failed to mark task %s as failed: %s", task_id, exc)
