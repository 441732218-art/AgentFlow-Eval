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
from app.core.evaluation.pipeline import (
    aggregate_pipeline_results,
    empty_pipeline_result,
    failed_pipeline_result,
    map_agent_status_to_trace,
    normalize_judge_result,
    partition_suite_results,
)
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
    """Factory for agent runners (OpenAI ReAct or HTTP); patchable in tests."""
    from app.core.agent_runner.factory import build_agent_runner as _factory

    return _factory(agent_config)


def build_llm_judge(judge_config: dict | None = None):
    """Factory for judges — plugin keys or default LLMJudge (patchable in tests).

    ``judge_config`` may include ``{"type": "length"}`` / ``{"judge": "length"}``
    to select a plugin-registered judge. Default remains LLMJudge.
    """
    cfg = dict(judge_config or {})
    judge_type = str(cfg.get("type") or cfg.get("judge") or "llm").lower().strip()
    if judge_type not in {"", "llm", "llm_judge", "default"}:
        try:
            from app.core.plugins.registry import get_capability_registry

            factory = get_capability_registry().get_judge_factory(judge_type)
            if factory is not None:
                return factory()
        except Exception:
            pass
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
def run_single_test_suite(
    self,
    test_suite_id: str,
    agent_config: dict,
    _trace_id: str | None = None,
) -> dict:
    """Execute one test case using OpenAIReActRunner and persist the Trace."""
    import time

    try:
        from app.core.observability.tracing import ensure_trace_id, set_trace_id

        if _trace_id:
            set_trace_id(str(_trace_id))
        else:
            ensure_trace_id()
    except Exception:
        pass

    try:
        from app.core.observability.aols import LogEvent, emit_evaluation

        emit_evaluation(
            LogEvent.EVALUATION_RUNNING,
            task_id=test_suite_id,
            phase="suite_started",
            celery_task=self,
            agent_model=(agent_config or {}).get("model"),
        )
    except Exception:
        pass
    logger.info("[Suite %s] Starting execution", test_suite_id)
    _t0 = time.perf_counter()

    async def _execute():
        async with async_session_factory() as session:
            result = await session.execute(
                select(TestSuite).where(TestSuite.id == test_suite_id)
            )
            suite = result.scalar_one_or_none()
            if not suite:
                raise ValueError(f"TestSuite not found: {test_suite_id}")

            # Resolve owning actor for metering / tenancy correlation
            actor_name = "anonymous"
            try:
                owner = await session.execute(
                    select(Task).where(Task.id == suite.task_id)
                )
                parent_task = owner.scalar_one_or_none()
                if parent_task is not None:
                    actor_name = getattr(parent_task, "created_by", None) or "anonymous"
            except Exception:
                pass

            from app.core.agent_runner.tool_sandbox import resolve_tools_for_suite
            from app.core.plugins.base import HOOK_POST_AGENT_RUN, HOOK_PRE_AGENT_RUN
            from app.core.plugins.hooks import get_hook_registry

            hooks = get_hook_registry()
            runner = build_agent_runner(agent_config or {})
            tools = resolve_tools_for_suite(suite.expected_tools)

            await hooks.emit(
                HOOK_PRE_AGENT_RUN,
                {
                    "test_suite_id": test_suite_id,
                    "query": suite.user_query,
                    "agent_config": agent_config or {},
                    "actor": actor_name,
                },
            )

            try:
                agent_result = await runner.run(
                    query=suite.user_query,
                    tools=tools,
                )
            except TypeError:
                # BaseAgentRunner signature: run(user_query, agent_config)
                agent_result = await runner.run(
                    suite.user_query,
                    agent_config or {},
                )
                if hasattr(agent_result, "__dataclass_fields__"):
                    from dataclasses import asdict

                    agent_result = asdict(agent_result)
                elif not isinstance(agent_result, dict):
                    agent_result = {
                        "steps": getattr(agent_result, "steps", []),
                        "total_tokens": getattr(agent_result, "total_tokens", 0),
                        "response_time_ms": getattr(agent_result, "response_time_ms", 0),
                        "status": getattr(agent_result, "status", "success"),
                        "error_message": getattr(agent_result, "error_message", ""),
                    }

            await hooks.emit(
                HOOK_POST_AGENT_RUN,
                {
                    "test_suite_id": test_suite_id,
                    "query": suite.user_query,
                    "actor": actor_name,
                    "status": (
                        agent_result.get("status")
                        if isinstance(agent_result, dict)
                        else getattr(agent_result, "status", "")
                    ),
                    "agent_result": agent_result
                    if isinstance(agent_result, dict)
                    else None,
                },
            )

            if not isinstance(agent_result, dict):
                agent_result = {
                    "steps": getattr(agent_result, "steps", []),
                    "total_tokens": getattr(agent_result, "total_tokens", 0),
                    "response_time_ms": getattr(agent_result, "response_time_ms", 0),
                    "status": getattr(agent_result, "status", "success"),
                    "error_message": getattr(agent_result, "error_message", ""),
                }

            mapped = map_agent_status_to_trace(agent_result.get("status", ""))
            trace_status = (
                TraceStatus.SUCCESS if mapped == "success" else TraceStatus.FAILED
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
                "actor": actor_name,
            }

    try:
        result = _run_async(_execute)
        duration_ms = int((time.perf_counter() - _t0) * 1000)
        logger.info(
            "[Suite %s] Completed: trace=%s status=%s tokens=%d",
            test_suite_id,
            result.get("trace_id"),
            result.get("status"),
            result.get("total_tokens", 0),
        )
        try:
            from app.core.observability.aols import LogEvent, emit_evaluation

            st = str(result.get("status") or "failed")
            emit_evaluation(
                LogEvent.EVALUATION_COMPLETED
                if st == "success"
                else LogEvent.EVALUATION_FAILED,
                task_id=str(result.get("task_id") or test_suite_id),
                status=st,
                duration_ms=duration_ms,
                total_tokens=int(result.get("total_tokens") or 0),
                celery_task=self,
                phase="suite",
                suite_trace_id=result.get("trace_id"),
                test_suite_id=test_suite_id,
            )
        except Exception:
            pass
        try:
            from app.core.observability.metrics import observe_suite_run

            observe_suite_run(
                status=str(result.get("status") or "failed"),
                duration_seconds=time.perf_counter() - _t0,
                agent_config=agent_config or {},
                total_tokens=int(result.get("total_tokens") or 0),
                actor=str(result.get("actor") or "anonymous"),
                ref_id=str(result.get("trace_id") or test_suite_id),
            )
        except Exception:
            pass
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - _t0) * 1000)
        logger.exception("[Suite %s] Execution failed: %s", test_suite_id, exc)
        try:
            from app.core.observability.aols import LogEvent, emit_evaluation

            emit_evaluation(
                LogEvent.EVALUATION_FAILED,
                task_id=test_suite_id,
                status="failed",
                duration_ms=duration_ms,
                celery_task=self,
                phase="suite",
                error_message=str(exc),
                test_suite_id=test_suite_id,
            )
        except Exception:
            pass
        try:
            from app.core.observability.metrics import observe_suite_run

            observe_suite_run(
                status="failed",
                duration_seconds=time.perf_counter() - _t0,
                agent_config=agent_config or {},
                actor="anonymous",
                ref_id=test_suite_id,
            )
        except Exception:
            pass
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
    self,
    trace_id: str,
    expected_output: str,
    expected_tools: list,
    _trace_id: str | None = None,
) -> dict:
    """Score one Trace using LLMJudge and persist the MetricScores."""
    import time

    try:
        from app.core.observability.tracing import ensure_trace_id, set_trace_id

        if _trace_id:
            set_trace_id(str(_trace_id))
        else:
            ensure_trace_id()
    except Exception:
        pass

    try:
        from app.core.observability.aols import LogEvent, emit_llm
        from app.core.observability.aols.emit import JUDGE

        emit_llm(
            LogEvent.LLM_STARTED,
            provider="judge",
            model="llm_judge",
            prompt_version="judge-default",
            stage=JUDGE,
            trace_id=trace_id,
        )
    except Exception:
        pass
    logger.info("[Judge %s] Starting evaluation", trace_id)
    _t0 = time.perf_counter()

    async def _judge():
        async with async_session_factory() as session:
            result = await session.execute(select(Trace).where(Trace.id == trace_id))
            trace = result.scalar_one_or_none()
            if not trace:
                raise ValueError(f"Trace not found: {trace_id}")

            # Trace → TestSuite → Task.created_by for metering actor
            actor_name = "anonymous"
            try:
                suite_r = await session.execute(
                    select(TestSuite).where(TestSuite.id == trace.test_suite_id)
                )
                suite = suite_r.scalar_one_or_none()
                if suite is not None:
                    task_r = await session.execute(
                        select(Task).where(Task.id == suite.task_id)
                    )
                    parent = task_r.scalar_one_or_none()
                    if parent is not None:
                        actor_name = getattr(parent, "created_by", None) or "anonymous"
            except Exception:
                pass

            from app.core.plugins.base import HOOK_POST_JUDGE, HOOK_PRE_JUDGE
            from app.core.plugins.hooks import get_hook_registry

            hooks = get_hook_registry()
            # Optional judge type from agent_config stored on related task is not
            # always available here; default LLMJudge / plugin via env later.
            judge = build_llm_judge()
            await hooks.emit(
                HOOK_PRE_JUDGE,
                {
                    "trace_id": trace_id,
                    "expected_output": expected_output,
                    "expected_tools": expected_tools or [],
                    "actor": actor_name,
                },
            )
            judge_result = await judge.evaluate(
                trace_steps=trace.steps,
                expected_output=expected_output,
                expected_tools=expected_tools or [],
            )
            await hooks.emit(
                HOOK_POST_JUDGE,
                {
                    "trace_id": trace_id,
                    "actor": actor_name,
                    "judge_result": judge_result
                    if isinstance(judge_result, dict)
                    else None,
                },
            )

            # Support both dict and object-style results via pure helper
            normalized = normalize_judge_result(judge_result)
            scores = normalized["scores"]
            total = normalized["total"]
            reason = normalized["reason"]
            token_cost = normalized["token_cost"]
            mode = (
                judge_result.get("mode", "rule_only")
                if isinstance(judge_result, dict)
                else getattr(judge_result, "mode", "rule_only")
            )

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
                "mode": mode or "rule_only",
                "actor": actor_name,
            }

    try:
        result = _run_async(_judge)
        duration_ms = int((time.perf_counter() - _t0) * 1000)
        logger.info(
            "[Judge %s] Completed: total=%.1f token_cost=%d",
            trace_id,
            result.get("total", 0),
            result.get("token_cost", 0),
        )
        try:
            from app.core.observability.aols import LogEvent, emit_llm
            from app.core.observability.aols.emit import JUDGE

            tok = int(result.get("token_cost") or 0)
            emit_llm(
                LogEvent.LLM_COMPLETED,
                provider="judge",
                model="llm_judge",
                prompt_version="judge-default",
                total_tokens=tok,
                latency_ms=duration_ms,
                stage=JUDGE,
                trace_id=trace_id,
                score_total=result.get("total"),
                mode=result.get("mode"),
            )
        except Exception:
            pass
        try:
            from app.core.observability.metrics import observe_judge

            observe_judge(
                mode=str(result.get("mode") or "rule_only"),
                status="ok",
                duration_seconds=time.perf_counter() - _t0,
                token_cost=int(result.get("token_cost") or 0),
                actor=str(result.get("actor") or "anonymous"),
                ref_id=trace_id,
            )
        except Exception:
            pass
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - _t0) * 1000)
        logger.exception("[Judge %s] Evaluation failed: %s", trace_id, exc)
        try:
            from app.core.observability.aols import LogEvent, emit_llm
            from app.core.observability.aols.emit import JUDGE

            emit_llm(
                LogEvent.LLM_FAILED,
                provider="judge",
                model="llm_judge",
                latency_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
                stage=JUDGE,
                trace_id=trace_id,
            )
        except Exception:
            pass
        try:
            from app.core.observability.metrics import observe_judge

            observe_judge(
                mode="unknown",
                status="error",
                duration_seconds=time.perf_counter() - _t0,
                actor="anonymous",
                ref_id=trace_id,
            )
        except Exception:
            pass
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
def run_full_evaluation(self, task_id: str, _trace_id: str | None = None) -> dict:
    """Orchestrate the full evaluation pipeline for a task.

    Pipeline:
      1. Load task + test suites from DB, set status to running
      2. Execute all suites in parallel (Celery group)
      3. Judge all traces in parallel
      4. Aggregate results
      5. Persist final status
    """
    import time

    # Restore HTTP TraceID from API enqueue (or mint a worker-local id)
    try:
        from app.core.observability.tracing import ensure_trace_id, set_trace_id

        if _trace_id:
            set_trace_id(str(_trace_id))
        else:
            ensure_trace_id()
    except Exception:
        pass

    logger.info("[Task %s] Full evaluation started trace_id=%s", task_id, _trace_id)
    try:
        from app.core.observability.aols import LogEvent, emit_evaluation

        emit_evaluation(
            LogEvent.EVALUATION_STARTED,
            task_id=task_id,
            celery_task=self,
            phase="pipeline",
            pipeline_trace_id=_trace_id,
        )
    except Exception:
        pass
    _t0 = time.perf_counter()
    _agent_config: dict[str, Any] = {}
    _tenant = "anonymous"
    try:
        from app.core.observability.tracing import get_trace_id

        _pipeline_trace = get_trace_id() or _trace_id
    except Exception:
        _pipeline_trace = _trace_id

    async def _orchestrate():
        nonlocal _agent_config, _tenant
        async with async_session_factory() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            _agent_config = dict(task.agent_config or {})
            _tenant = getattr(task, "created_by", None) or "anonymous"

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
                return empty_pipeline_result(task_id)

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

            # Execute suites (group with eager mode runs inline); propagate TraceID
            suite_jobs = [
                run_single_test_suite.s(
                    suite.id,
                    task.agent_config or {},
                    _pipeline_trace,
                )
                for suite in suites
            ]
            suite_group = group(suite_jobs)
            suite_async = suite_group.apply_async()
            suite_results = suite_async.get(disable_sync_subtasks=False)

            # Normalize results list
            if not isinstance(suite_results, (list, tuple)):
                suite_results = [suite_results]

            successful_suites, failed_suites = partition_suite_results(suite_results)

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
                            _pipeline_trace,
                        )
                    )

            if judge_jobs:
                judge_async = group(judge_jobs).apply_async()
                judge_results = judge_async.get(disable_sync_subtasks=False)
                if not isinstance(judge_results, (list, tuple)):
                    judge_results = [judge_results]
            else:
                judge_results = []

            summary = aggregate_pipeline_results(suite_results, judge_results)
            overall_status = summary["overall_status"]

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
                        "completed_suites": summary["completed_suites"],
                        "failed_suites": summary["failed_suites"],
                        "average_score": summary["average_score"],
                    },
                )
            except Exception:
                pass

            return {
                "task_id": task_id,
                "status": overall_status,
                "total_suites": total,
                "completed_suites": summary["completed_suites"],
                "failed_suites": summary["failed_suites"],
                "average_score": summary["average_score"],
                "dimension_scores": summary["dimension_scores"],
                "total_tokens": summary["total_tokens"],
                "total_time_ms": summary["total_time_ms"],
                "suites": list(suite_results),
                "judgments": list(judge_results),
            }

    try:
        result = _run_async(_orchestrate)
        duration_ms = int((time.perf_counter() - _t0) * 1000)
        logger.info(
            "[Task %s] Completed: status=%s suites=%d/%d score=%.1f",
            task_id,
            result.get("status"),
            result.get("completed_suites", 0),
            result.get("total_suites", 0),
            result.get("average_score", 0.0),
        )
        try:
            from app.core.observability.aols import LogEvent, emit_evaluation

            st = str(result.get("status") or "completed")
            emit_evaluation(
                LogEvent.EVALUATION_FAILED
                if st == "failed"
                else LogEvent.EVALUATION_COMPLETED,
                task_id=task_id,
                status=st,
                duration_ms=duration_ms,
                total_tokens=int(result.get("total_tokens") or 0),
                average_score=float(result.get("average_score") or 0.0),
                celery_task=self,
                phase="pipeline",
                completed_suites=result.get("completed_suites"),
                failed_suites=result.get("failed_suites"),
                total_suites=result.get("total_suites"),
            )
        except Exception:
            pass
        try:
            from app.core.observability.metrics import observe_evaluation

            observe_evaluation(
                status=str(result.get("status") or "completed"),
                duration_seconds=time.perf_counter() - _t0,
                tenant=_tenant,
                agent_config=_agent_config,
                total_tokens=int(result.get("total_tokens") or 0),
            )
        except Exception:
            pass
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - _t0) * 1000)
        logger.exception("[Task %s] Orchestration failed: %s", task_id, exc)
        try:
            from app.core.observability.aols import LogEvent, emit_evaluation

            emit_evaluation(
                LogEvent.EVALUATION_FAILED,
                task_id=task_id,
                status="failed",
                duration_ms=duration_ms,
                celery_task=self,
                phase="pipeline",
                error_message=str(exc),
            )
        except Exception:
            pass
        _run_async(lambda: _mark_task_failed(task_id, str(exc)))
        try:
            from app.core.observability.metrics import (
                observe_evaluation,
                observe_stage_error,
            )

            observe_stage_error(stage="pipeline", status="failed")
            observe_evaluation(
                status="failed",
                duration_seconds=time.perf_counter() - _t0,
                tenant=_tenant,
                agent_config=_agent_config,
            )
        except Exception:
            pass
        return failed_pipeline_result(task_id, str(exc))


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
