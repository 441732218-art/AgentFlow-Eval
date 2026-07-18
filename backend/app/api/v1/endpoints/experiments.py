# (c) 2026 AgentFlow-Eval
"""Experiment APIs — create multi-variant evaluations and compare scores."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import write_audit
from app.core.dependencies import get_db
from app.core.evaluation.compare import (
    aggregate_task_scores,
    deltas_vs_best,
    pick_best_label,
)
from app.core.rbac import Permission, get_request_role, require_permission
from app.core.tenancy import ensure_task_access
from app.models.experiment import Experiment, ExperimentRun
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace
from app.schemas.experiment import (
    ExperimentCompareResponse,
    ExperimentCreate,
    ExperimentListResponse,
    ExperimentResponse,
    ExperimentRunResponse,
    RunCompareItem,
    SuiteCase,
)
from app.utils.exceptions import BusinessError, NotFoundError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


async def _load_suites_from_task(
    session: AsyncSession,
    task_id: str,
    actor: str,
) -> list[dict[str, Any]]:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    ensure_task_access(task, actor, task_id)
    suites = await session.execute(
        select(TestSuite).where(TestSuite.task_id == task_id)
    )
    return [
        {
            "user_query": s.user_query,
            "expected_output": s.expected_output or "",
            "expected_tools": list(s.expected_tools or []),
        }
        for s in suites.scalars().all()
    ]


def _merge_suite_snapshot(
    from_task: list[dict[str, Any]],
    explicit: list[SuiteCase],
) -> list[dict[str, Any]]:
    merged = list(from_task)
    for s in explicit:
        merged.append(
            {
                "user_query": s.user_query,
                "expected_output": s.expected_output,
                "expected_tools": list(s.expected_tools or []),
            }
        )
    return merged


async def _queue_task(task_id: str) -> str | None:
    """Enqueue full evaluation via TaskQueuePort; return job id if available."""
    try:
        from app.core.profiles import get_task_queue
        from app.core.observability.tracing import get_trace_id

        tid = get_trace_id() or None
        enq = get_task_queue().enqueue(
            "run_full_evaluation",
            args=(task_id,),
            kwargs={"_trace_id": tid} if tid else None,
        )
        return enq.task_id
    except Exception:
        # Last-resort inline call (tests / misconfigured broker)
        try:
            from app.core.celery_app.tasks import run_full_evaluation

            run_full_evaluation(task_id)
        except Exception:
            pass
        return None


def _experiment_to_response(
    exp: Experiment,
    runs: list[ExperimentRun],
    task_status_map: dict[str, str] | None = None,
) -> ExperimentResponse:
    status_map = task_status_map or {}
    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        description=exp.description or "",
        base_task_id=exp.base_task_id,
        suite_count=len(exp.suite_snapshot or []),
        created_by=exp.created_by or "anonymous",
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        runs=[
            ExperimentRunResponse(
                id=r.id,
                experiment_id=r.experiment_id,
                task_id=r.task_id,
                label=r.label,
                agent_config=r.agent_config or {},
                task_status=status_map.get(r.task_id),
                created_at=r.created_at,
            )
            for r in runs
        ],
    )


@router.post("", response_model=ExperimentResponse, status_code=201)
@require_permission(Permission.TASK_CREATE, Permission.TASK_EXECUTE)
async def create_experiment(
    body: ExperimentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    """Create an experiment, materialize one Task per variant, optionally execute."""
    actor = _actor(request)

    from_task: list[dict[str, Any]] = []
    if body.base_task_id:
        from_task = await _load_suites_from_task(session, body.base_task_id, actor)

    snapshot = _merge_suite_snapshot(from_task, body.suites)
    if not snapshot:
        raise BusinessError(
            "Experiment requires at least one suite "
            "(provide base_task_id with suites and/or suites[])"
        )

    exp = Experiment(
        name=body.name,
        description=body.description or "",
        base_task_id=body.base_task_id,
        suite_snapshot=snapshot,
        created_by=actor,
    )
    session.add(exp)
    await session.flush()

    runs: list[ExperimentRun] = []
    status_map: dict[str, str] = {}

    for variant in body.variants:
        task = Task(
            name=f"{body.name} [{variant.label}]",
            description=f"Experiment run: {body.name} / {variant.label}",
            agent_config=dict(variant.agent_config or {}),
            status=TaskStatus.CREATED,
            created_by=actor,
        )
        session.add(task)
        await session.flush()

        for case in snapshot:
            session.add(
                TestSuite(
                    task_id=task.id,
                    user_query=case["user_query"],
                    expected_output=case.get("expected_output") or "",
                    expected_tools=list(case.get("expected_tools") or []),
                )
            )

        run = ExperimentRun(
            experiment_id=exp.id,
            task_id=task.id,
            label=variant.label,
            agent_config=dict(variant.agent_config or {}),
        )
        session.add(run)
        runs.append(run)

        if body.auto_execute:
            task.status = TaskStatus.QUEUED
            await session.flush()
            celery_id = await _queue_task(task.id)
            if celery_id:
                task.celery_task_id = celery_id
            status_map[task.id] = task.status.value
        else:
            status_map[task.id] = task.status.value

    await session.commit()
    await session.refresh(exp)
    for r in runs:
        await session.refresh(r)

    await write_audit(
        session,
        action="experiment.create",
        resource_type="experiment",
        resource_id=exp.id,
        actor=actor,
        detail={"variants": [v.label for v in body.variants], "suite_count": len(snapshot)},
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()

    return _experiment_to_response(exp, runs, status_map)


@router.get("", response_model=ExperimentListResponse)
@require_permission(Permission.TASK_READ)
async def list_experiments(
    request: Request,
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ExperimentListResponse:
    """List experiments for the current actor (admin sees all when tenancy on)."""
    actor = _actor(request)
    from app.config import settings
    from app.core.tenancy import is_admin

    q = select(Experiment)
    count_q = select(func.count(Experiment.id))
    if settings.AUTH_ENABLED or settings.TENANCY_ENABLED:
        if not is_admin(actor):
            q = q.where(Experiment.created_by == actor)
            count_q = count_q.where(Experiment.created_by == actor)

    total = int((await session.execute(count_q)).scalar() or 0)
    rows = list(
        (
            await session.execute(
                q.order_by(Experiment.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
    )

    # Batch-load runs + task statuses for the page (avoid N+1)
    exp_ids = [e.id for e in rows]
    runs_by_exp: dict[str, list[ExperimentRun]] = {eid: [] for eid in exp_ids}
    all_task_ids: list[str] = []
    if exp_ids:
        all_runs = list(
            (
                await session.execute(
                    select(ExperimentRun).where(
                        ExperimentRun.experiment_id.in_(exp_ids)
                    )
                )
            ).scalars().all()
        )
        for run in all_runs:
            runs_by_exp.setdefault(run.experiment_id, []).append(run)
            all_task_ids.append(run.task_id)

    status_map: dict[str, str] = {}
    if all_task_ids:
        tasks = (
            await session.execute(select(Task).where(Task.id.in_(all_task_ids)))
        ).scalars().all()
        status_map = {t.id: t.status.value for t in tasks}

    items = [
        _experiment_to_response(exp, runs_by_exp.get(exp.id, []), status_map)
        for exp in rows
    ]

    return ExperimentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
@require_permission(Permission.TASK_READ)
async def get_experiment(
    experiment_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    """Get experiment detail with run statuses."""
    actor = _actor(request)
    exp = await _get_experiment_or_404(session, experiment_id, actor)
    runs = (
        await session.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == exp.id)
        )
    ).scalars().all()
    task_ids = [r.task_id for r in runs]
    status_map: dict[str, str] = {}
    if task_ids:
        tasks = (
            await session.execute(select(Task).where(Task.id.in_(task_ids)))
        ).scalars().all()
        status_map = {t.id: t.status.value for t in tasks}
    return _experiment_to_response(exp, list(runs), status_map)


@router.get("/{experiment_id}/compare", response_model=ExperimentCompareResponse)
@require_permission(Permission.EVALUATION_READ)
async def compare_experiment(
    experiment_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ExperimentCompareResponse:
    """Side-by-side score comparison across experiment runs."""
    actor = _actor(request)
    exp = await _get_experiment_or_404(session, experiment_id, actor)
    runs = (
        await session.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == exp.id)
        )
    ).scalars().all()

    compare_items: list[RunCompareItem] = []
    raw_for_best: list[dict[str, Any]] = []

    for run in runs:
        task = (
            await session.execute(select(Task).where(Task.id == run.task_id))
        ).scalar_one_or_none()
        status = task.status.value if task else "unknown"

        suite_result = await session.execute(
            select(TestSuite)
            .options(
                selectinload(TestSuite.traces).selectinload(Trace.metric_scores),
            )
            .where(TestSuite.task_id == run.task_id)
        )
        suites = suite_result.scalars().all()
        suite_rows: list[dict[str, Any]] = []
        for suite in suites:
            traces_payload = []
            for trace in suite.traces or []:
                scores = {ms.metric_name: ms.score for ms in (trace.metric_scores or [])}
                # Also expose synthetic total as sum of dimensions for average_score
                if scores:
                    scores = {**scores, "total": sum(scores.values())}
                traces_payload.append(
                    {
                        "total_tokens": trace.total_tokens,
                        "response_time_ms": trace.response_time_ms,
                        "scores": scores,
                    }
                )
            suite_rows.append({"traces": traces_payload})

        agg = aggregate_task_scores(suite_rows)
        item = RunCompareItem(
            label=run.label,
            task_id=run.task_id,
            task_status=status,
            average_score=agg["average_score"],
            dimension_scores=agg["dimension_scores"],
            total_tokens=agg["total_tokens"],
            total_time_ms=agg["total_time_ms"],
            suite_count=agg["suite_count"],
            scored_traces=agg["scored_traces"],
        )
        compare_items.append(item)
        raw_for_best.append(item.model_dump())

    best = pick_best_label(raw_for_best)
    deltas = deltas_vs_best(raw_for_best, best)

    return ExperimentCompareResponse(
        experiment_id=exp.id,
        name=exp.name,
        suite_count=len(exp.suite_snapshot or []),
        runs=compare_items,
        best_label=best,
        delta_vs_best=deltas,
    )


async def _get_experiment_or_404(
    session: AsyncSession,
    experiment_id: str,
    actor: str,
) -> Experiment:
    from app.config import settings
    from app.core.tenancy import is_admin

    result = await session.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    exp = result.scalar_one_or_none()
    if exp is None:
        raise NotFoundError("Experiment", experiment_id)
    if settings.AUTH_ENABLED or settings.TENANCY_ENABLED:
        if not is_admin(actor) and exp.created_by != actor:
            raise NotFoundError("Experiment", experiment_id)
    return exp
