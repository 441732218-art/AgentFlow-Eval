# (c) 2026 AgentFlow-Eval
"""Diagnosis API — AI-style failure analysis for Intelligence Center."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.diagnosis.engine import diagnose_from_traces, diagnose_task
from app.core.rbac import Permission, require_permission
from app.core.tenancy import apply_owner_filter, load_trace_with_access
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.utils.exceptions import NotFoundError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


@router.get("")
@require_permission(Permission.EVALUATION_READ)
async def list_recent_diagnoses(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return diagnosis summaries for recent failed / completed tasks."""
    actor = _actor(request)

    q = (
        select(Task)
        .where(
            Task.status.in_(
                [
                    TaskStatus.FAILED,
                    TaskStatus.TIMEOUT,
                    TaskStatus.COMPLETED,
                ]
            )
        )
        .order_by(Task.updated_at.desc())
        .limit(limit)
    )
    q = apply_owner_filter(q, actor)
    tasks = list((await session.execute(q)).scalars().all())

    items: list[dict[str, Any]] = []
    for task in tasks:
        d = await diagnose_task(session, task.id, actor=actor)
        if d:
            items.append(
                {
                    "task_id": d.get("task_id"),
                    "task_name": d.get("task_name"),
                    "task_status": d.get("task_status"),
                    "issue": d.get("issue"),
                    "confidence": d.get("confidence"),
                    "root_cause": d.get("root_cause"),
                    "suggestion": d.get("suggestion"),
                }
            )
    return {"items": items, "total": len(items)}


@router.get("/trace/{trace_id}")
@require_permission(Permission.EVALUATION_READ)
async def get_trace_diagnosis(
    trace_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Diagnose a single trace."""
    trace = await load_trace_with_access(session, trace_id, _actor(request))
    suite = (
        await session.execute(
            select(TestSuite).where(TestSuite.id == trace.test_suite_id)
        )
    ).scalar_one_or_none()
    task = None
    if suite:
        task = (
            await session.execute(select(Task).where(Task.id == suite.task_id))
        ).scalar_one_or_none()
    return diagnose_from_traces(
        task=task,
        traces=[trace],
        suites=[suite] if suite else [],
    )


@router.get("/{task_id}")
@require_permission(Permission.EVALUATION_READ)
async def get_task_diagnosis(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Diagnose a task: issue, confidence, root_cause, suggestion + topology."""
    result = await diagnose_task(session, task_id, actor=_actor(request))
    if result is None:
        raise NotFoundError("任务", task_id)
    return result
