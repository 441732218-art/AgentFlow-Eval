# (c) 2026 AgentFlow-Eval
"""Celery async evaluation pipeline.

Architecture:
  Connects OpenAIReActRunner and LLMJudge into an automated pipeline:

    run_full_evaluation(task_id)
         │
         ├── 1. Load Task + TestSuites from DB
         ├── 2. Update status to "running"
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

import logging

from celery import chain, group
from sqlalchemy import select

from app.core.celery_app.celery import celery_app
from app.core.dependencies import async_session_factory
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace, TraceStatus

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine inside a synchronous Celery worker."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Sub-task 1: Execute a single test suite via OpenAIReActRunner
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300, time_limit=320, acks_late=True, autoretry_for=(ConnectionError, TimeoutError, OSError), retry_backoff=True, retry_backoff_max=600)
def run_single_test_suite(self, test_suite_id: str, agent_config: dict) -> dict:
    """Execute one test case using OpenAIReActRunner and persist the Trace.

    Args:
        test_suite_id: TestSuite UUID.
        agent_config: Agent configuration dict (model, temperature, etc.).

    Returns:
        dict with trace_id, status, total_tokens, response_time_ms,
        step_count, final_answer, and error_message on failure.
    """
    logger.info("[Suite %s] Starting execution", test_suite_id)

    async def _execute():
        async with async_session_factory() as session:
            result = await session.execute(
                select(TestSuite).where(TestSuite.id == test_suite_id)
            )
            suite = result.scalar_one_or_none()
            if not suite:
                raise ValueError(f"TestSuite not found: {test_suite_id}")

            # Use the new OpenAIReActRunner (supports multi-turn ReAct loop)
            from app.core.agent_runner.openai_runner import OpenAIReActRunner

            runner = OpenAIReActRunner(
                model=agent_config.get("model", "gpt-4o-mini"),
                max_iterations=agent_config.get("max_iterations", 5),
            )

            # Prepare tool definitions from the test suite's expected tools
            tools = [
                {
                    "name": t,
                    "description": f"Tool: {t}",
                    "parameters": {},
                }
                for t in (suite.expected_tools or [])
            ] or None

            agent_result = await runner.run(
                query=suite.user_query,
                tools=tools,
            )

            # Map agent status to TraceStatus
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
        result = _run_async(_execute())
        logger.info(
            "[Suite %s] Completed: trace=%s status=%s tokens=%d",
            test_suite_id, result.get("trace_id"), result.get("status"),
            result.get("total_tokens", 0),
        )
        return result
    except Exception as exc:
        logger.exception("[Suite %s] Execution failed: %s", test_suite_id, exc)
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300, time_limit=320, acks_late=True, autoretry_for=(ConnectionError, TimeoutError, OSError), retry_backoff=True, retry_backoff_max=600)
def run_judge_evaluation(
    self, trace_id: str, expected_output: str, expected_tools: list
) -> dict:
    """Score one Trace using LLMJudge and persist the MetricScores.

    Args:
        trace_id: Trace UUID.
        expected_output: Expected final answer text.
        expected_tools: Expected tool names.

    Returns:
        dict with trace_id, scores, total, reason, token_cost, and
        error_message on failure.
    """
    logger.info("[Judge %s] Starting evaluation", trace_id)

    async def _judge():
        async with async_session_factory() as session:
            result = await session.execute(
                select(Trace).where(Trace.id == trace_id)
            )
            trace = result.scalar_one_or_none()
            if not trace:
                raise ValueError(f"Trace not found: {trace_id}")

            from app.core.judge_engine.llm_judge import LLMJudge

            judge = LLMJudge()
            judge_result = await judge.evaluate(
                trace_steps=trace.steps,
                expected_output=expected_output,
                expected_tools=expected_tools,
            )

            # judge_result is a dict with scores/total/reason/token_cost
            scores = judge_result.get("scores", {})
            total = judge_result.get("total", 0.0)
            reason = judge_result.get("reason", "")
            token_cost = judge_result.get("token_cost", 0)

            # Persist each dimension score as a separate MetricScore row
            for metric_name, score in scores.items():
                ms = MetricScore(
                    trace_id=trace_id,
                    metric_name=metric_name,
                    score=score,
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
        result = _run_async(_judge())
        logger.info(
            "[Judge %s] Completed: total=%.1f token_cost=%d",
            trace_id, result.get("total", 0), result.get("token_cost", 0),
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

    Progress is reported via ``self.update_state()`` so the API can
    poll for intermediate status.

    Args:
        task_id: Task UUID.

    Returns:
        Aggregate dict with summary statistics.
    """
    logger.info("[Task %s] Full evaluation started", task_id)

    async def _orchestrate():
        async with async_session_factory() as session:
            # 1. Load task
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                raise ValueError(f"Task not found: {task_id}")

            task.status = TaskStatus.RUNNING
            await session.commit()

            # 2. Load test suites
            suite_result = await session.execute(
                select(TestSuite).where(TestSuite.task_id == task_id)
            )
            suites = list(suite_result.scalars().all())

            if not suites:
                task.status = TaskStatus.COMPLETED
                await session.commit()
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "total_suites": 0,
                    "message": "No test suites found.",
                }

            total = len(suites)
            self.update_state(state="RUNNING", meta={
                "task_id": task_id, "phase": "executing",
                "total_suites": total, "completed": 0,
            })

            # 3. Execute all test suites in parallel
            suite_jobs = [
                run_single_test_suite.s(suite.id, task.agent_config)
                for suite in suites
            ]
            suite_results = group(suite_jobs)().get()

            # Separate successful and failed executions
            successful_suites = [
                r for r in suite_results
                if r.get("trace_id") and r.get("status") != "failed"
            ]
            failed_suites = [
                r for r in suite_results
                if not r.get("trace_id") or r.get("status") == "failed"
            ]

            self.update_state(state="RUNNING", meta={
                "task_id": task_id, "phase": "judging",
                "total_suites": total,
                "completed_suites": len(successful_suites),
                "failed_suites": len(failed_suites),
            })

            # 4. Judge all successful traces in parallel
            judge_jobs = []
            judge_suite_map = {}  # trace_id -> suite for error reporting

            for suite, s_result in zip(suites, suite_results):
                tid = s_result.get("trace_id")
                if tid:
                    judge_jobs.append(
                        run_judge_evaluation.s(
                            tid,
                            suite.expected_output,
                            suite.expected_tools,
                        )
                    )
                    judge_suite_map[tid] = suite

            judge_results = group(judge_jobs)().get() if judge_jobs else []

            # 5. Aggregate results
            total_score = 0.0
            score_count = 0
            dimension_scores: dict[str, list[float]] = {}
            total_tokens = 0
            total_time_ms = 0

            for jr in judge_results:
                total_score += jr.get("total", 0.0)
                score_count += 1
                total_tokens += jr.get("token_cost", 0)
                for dim, val in jr.get("scores", {}).items():
                    dimension_scores.setdefault(dim, []).append(val)

            for s_result in suite_results:
                total_tokens += s_result.get("total_tokens", 0)
                total_time_ms += s_result.get("response_time_ms", 0)

            avg_score = round(total_score / score_count, 1) if score_count else 0.0
            avg_dim_scores = {
                dim: round(sum(vals) / len(vals), 1)
                for dim, vals in dimension_scores.items()
            } if dimension_scores else {}

            # Determine overall status
            overall_status = "completed"
            if failed_suites and not successful_suites:
                overall_status = "failed"
            elif failed_suites:
                overall_status = "partial"

            task.status = (
                TaskStatus.FAILED if overall_status == "failed"
                else TaskStatus.COMPLETED
            )
            await session.commit()

            self.update_state(state=overall_status.upper(), meta={
                "task_id": task_id, "phase": "done",
                "total_suites": total,
                "completed_suites": len(successful_suites),
                "failed_suites": len(failed_suites),
                "average_score": avg_score,
            })

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
                "suites": suite_results,
                "judgments": judge_results,
            }

    try:
        result = _run_async(_orchestrate())
        logger.info(
            "[Task %s] Completed: status=%s suites=%d/%d score=%.1f",
            task_id, result.get("status"),
            result.get("completed_suites", 0),
            result.get("total_suites", 0),
            result.get("average_score", 0.0),
        )
        return result
    except Exception as exc:
        logger.exception("[Task %s] Orchestration failed: %s", task_id, exc)
        # Mark task as failed
        _run_async(_mark_task_failed(task_id, str(exc)))
        return {
            "task_id": task_id,
            "status": "failed",
            "error_message": str(exc),
        }


async def _mark_task_failed(task_id: str, error: str) -> None:
    """Mark a task as failed in the database."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                task.status = TaskStatus.FAILED
                await session.commit()
    except Exception as exc:
        logger.error("Failed to mark task %s as failed: %s", task_id, exc)
