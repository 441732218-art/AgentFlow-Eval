# (c) 2026 AgentFlow-Eval
"""Domain cache services: task detail/list, dashboard, eval results."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.client import get_cache
from app.core.cache.keys import (
    CacheTTL,
    dashboard_key,
    eval_result_key,
    settings_public_key,
    task_detail_key,
    task_list_key,
    task_list_version_key,
)
from app.core.db.queries import batch_suite_counts
from app.core.tenancy import apply_owner_filter
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace


def _task_dict(task: Task, suite_count: int = 0) -> dict[str, Any]:
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "agent_config": task.agent_config or {},
        "celery_task_id": task.celery_task_id,
        "is_archived": bool(getattr(task, "is_archived", False)),
        "created_by": getattr(task, "created_by", None) or "anonymous",
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "test_suite_count": suite_count,
    }


async def get_cached_task_detail(
    session: AsyncSession,
    task: Task,
) -> dict[str, Any]:
    """Cache-aside task detail (TTL 5 min)."""
    cache = get_cache()
    key = task_detail_key(task.id)
    hit = await cache.get(key)
    if hit is not None:
        return hit
    counts = await batch_suite_counts(session, [task.id])
    payload = _task_dict(task, counts.get(task.id, 0))
    await cache.set(key, payload, ttl=int(CacheTTL.TASK_DETAIL))
    return payload


async def set_cached_task_detail(task: Task, suite_count: int = 0) -> None:
    """Write-through after create/update."""
    await get_cache().set(
        task_detail_key(task.id),
        _task_dict(task, suite_count),
        ttl=int(CacheTTL.TASK_DETAIL),
    )


async def serialize_task_list(
    session: AsyncSession,
    *,
    actor: str,
    role: str | None,
    page: int,
    page_size: int,
    status: str | None,
    include_archived: bool,
) -> dict[str, Any]:
    """Build task list payload (used for cache fill and direct response)."""
    query = select(Task)
    count_query = select(func.count(Task.id))
    query = apply_owner_filter(query, actor, role=role)
    count_query = apply_owner_filter(count_query, actor, role=role)
    if not include_archived:
        query = query.where(Task.is_archived.is_(False))
        count_query = count_query.where(Task.is_archived.is_(False))
    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    query = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(
        page_size
    )
    total = int((await session.execute(count_query)).scalar() or 0)
    tasks = list((await session.execute(query)).scalars().all())
    counts = await batch_suite_counts(session, [t.id for t in tasks])
    items = [_task_dict(t, counts.get(t.id, 0)) for t in tasks]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_cached_task_list(
    session: AsyncSession,
    *,
    actor: str,
    role: str | None,
    page: int,
    page_size: int,
    status: str | None,
    include_archived: bool,
) -> dict[str, Any]:
    """Cache-aside task list (TTL 30s, versioned by actor)."""
    cache = get_cache()
    ver = await cache.get(task_list_version_key(actor)) or 0
    key = task_list_key(
        actor,
        ver,
        page=page,
        page_size=page_size,
        status=status,
        include_archived=include_archived,
    )
    hit = await cache.get(key)
    if hit is not None:
        return hit
    payload = await serialize_task_list(
        session,
        actor=actor,
        role=role,
        page=page,
        page_size=page_size,
        status=status,
        include_archived=include_archived,
    )
    await cache.set(key, payload, ttl=int(CacheTTL.TASK_LIST))
    return payload


async def build_dashboard_stats(
    session: AsyncSession,
    *,
    actor: str,
    role: str | None = None,
) -> dict[str, Any]:
    """Aggregate counts for dashboard widgets."""
    base = select(Task)
    base = apply_owner_filter(base, actor, role=role)
    base = base.where(Task.is_archived.is_(False))

    async def _count(extra=None) -> int:
        q = select(func.count(Task.id))
        q = apply_owner_filter(q, actor, role=role)
        q = q.where(Task.is_archived.is_(False))
        if extra is not None:
            q = q.where(extra)
        return int((await session.execute(q)).scalar() or 0)

    total = await _count()
    by_status: dict[str, int] = {}
    for st in TaskStatus:
        by_status[st.value] = await _count(Task.status == st)

    suite_q = (
        select(func.count(TestSuite.id))
        .select_from(TestSuite)
        .join(Task, TestSuite.task_id == Task.id)
        .where(Task.is_archived.is_(False))
    )
    # Apply same ownership rules as task list
    from app.core.tenancy import is_admin, tenancy_enforced

    if tenancy_enforced() and not is_admin(actor):
        cross = False
        if role:
            try:
                from app.core.rbac import CROSS_TENANT_ROLES, Role, rbac_enforced

                if rbac_enforced():
                    cross = Role.parse(str(role)) in CROSS_TENANT_ROLES
            except Exception:
                cross = False
        if not cross:
            suite_q = suite_q.where(Task.created_by == (actor or "anonymous"))

    suite_total = int((await session.execute(suite_q)).scalar() or 0)

    return {
        "actor": actor or "anonymous",
        "tasks_total": total,
        "tasks_by_status": by_status,
        "suites_total": suite_total,
        "active_tasks": by_status.get("running", 0)
        + by_status.get("queued", 0)
        + by_status.get("judging", 0),
        "completed_tasks": by_status.get("completed", 0),
        "failed_tasks": by_status.get("failed", 0),
    }


async def get_cached_dashboard(
    session: AsyncSession,
    *,
    actor: str,
    role: str | None = None,
) -> dict[str, Any]:
    """Cache-aside dashboard stats (TTL 1 min)."""
    cache = get_cache()
    key = dashboard_key(actor)
    hit = await cache.get(key)
    if hit is not None:
        return hit
    stats = await build_dashboard_stats(session, actor=actor, role=role)
    await cache.set(key, stats, ttl=int(CacheTTL.DASHBOARD))
    return stats


async def get_cached_eval_result(
    trace_id: str,
    version: str,
    factory,
) -> dict[str, Any]:
    """Versioned evaluation result cache (TTL 1h)."""
    cache = get_cache()
    key = eval_result_key(trace_id, version)
    hit = await cache.get(key)
    if hit is not None:
        return hit
    value = await factory()
    await cache.set(key, value, ttl=int(CacheTTL.EVAL_RESULT))
    return value


async def get_cached_settings_public(factory) -> dict[str, Any]:
    """Cache-aside public settings (TTL 10 min)."""
    cache = get_cache()
    key = settings_public_key()
    hit = await cache.get(key)
    if hit is not None:
        return hit
    value = await factory()
    await cache.set(key, value, ttl=int(CacheTTL.SETTINGS))
    return value


def eval_version_from_scores(scores: list[MetricScore] | None) -> str:
    """Build a stable version stamp from metric scores for cache keys."""
    if not scores:
        return "empty"
    parts = []
    for ms in scores:
        parts.append(
            f"{ms.metric_name}:{ms.score}:{ms.is_human_reviewed}:{ms.human_score}"
        )
    raw = "|".join(sorted(parts))
    import hashlib

    return hashlib.sha256(raw.encode()).hexdigest()[:12]
