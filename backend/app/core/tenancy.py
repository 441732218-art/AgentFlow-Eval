# (c) 2026 AgentFlow-Eval
"""Actor isolation + enterprise tenant filtering helpers."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.task import Task
from app.models.test_suite import TestSuite
from app.models.trace import Trace
from app.utils.exceptions import NotFoundError


def tenancy_enforced() -> bool:
    """Isolation is on when auth is enabled, or TENANCY_ENABLED is explicit."""
    return bool(settings.AUTH_ENABLED or settings.TENANCY_ENABLED)


def admin_actors() -> set[str]:
    raw = settings.ADMIN_ACTORS or ""
    return {p.strip() for p in raw.split(",") if p.strip()}


def is_admin(actor: str | None) -> bool:
    if not actor:
        return False
    return actor in admin_actors()


def can_access_task(
    task: Task,
    actor: str | None,
    *,
    role: str | None = None,
) -> bool:
    """Return True if actor may read/mutate the task.

    Cross-owner access is granted to ADMIN/MANAGER/REVIEWER / enterprise
    system_admin / tenant_admin roles when RBAC is active; otherwise falls
    back to ADMIN_ACTORS + ownership checks.

    When multi-tenant is on and a tenant is selected, also enforce tenant_id.
    """
    # Tenant boundary first
    try:
        from app.core.tenant_context import (
            current_tenant_id,
            multi_tenant_enabled,
        )

        if multi_tenant_enabled():
            tid = current_tenant_id()
            if tid:
                resource_tid = getattr(task, "tenant_id", None)
                if resource_tid and resource_tid != tid:
                    return False
                if not resource_tid:
                    # Legacy row without tenant: deny when tenant scoped
                    return False
    except Exception:
        pass

    if not tenancy_enforced():
        return True
    if is_admin(actor):
        return True
    # Role-based cross-owner (RBAC)
    try:
        from app.core.rbac import CROSS_OWNER_ROLES, Role, rbac_enforced

        if rbac_enforced() and role:
            try:
                r = Role.parse(str(role))
                if r in CROSS_OWNER_ROLES:
                    return True
            except ValueError:
                pass
    except Exception:
        pass
    owner = getattr(task, "created_by", None) or "anonymous"
    return owner == (actor or "anonymous")


def ensure_task_access(
    task: Task | None,
    actor: str | None,
    task_id: str = "",
    *,
    role: str | None = None,
) -> Task:
    """Raise NotFoundError if missing or not accessible (no existence leak)."""
    if task is None or not can_access_task(task, actor, role=role):
        raise NotFoundError("Task", task_id or (task.id if task else ""))
    return task


def apply_owner_filter(
    query: Select,
    actor: str | None,
    *,
    role: str | None = None,
) -> Select:
    """Restrict Task list queries to the current actor when tenancy is on.

    Also applies ``tenant_id`` filter when multi-tenant context is active.
    """
    try:
        from app.core.tenant_context import apply_tenant_filter

        query = apply_tenant_filter(query, Task)
    except Exception:
        pass

    if not tenancy_enforced():
        return query
    if is_admin(actor):
        return query
    try:
        from app.core.rbac import CROSS_OWNER_ROLES, Role, rbac_enforced

        if rbac_enforced() and role:
            try:
                if Role.parse(str(role)) in CROSS_OWNER_ROLES:
                    return query
            except ValueError:
                pass
    except Exception:
        pass
    owner = actor or "anonymous"
    return query.where(Task.created_by == owner)


def apply_trace_owner_filter(query: Select, actor: str | None) -> Select:
    """Restrict Trace queries to suites belonging to actor-owned tasks."""
    try:
        from app.core.tenant_context import apply_tenant_filter

        query = apply_tenant_filter(query, Trace)
    except Exception:
        pass

    if not tenancy_enforced():
        return query
    if is_admin(actor):
        return query
    owner = actor or "anonymous"
    return (
        query.join(TestSuite, Trace.test_suite_id == TestSuite.id)
        .join(Task, TestSuite.task_id == Task.id)
        .where(Task.created_by == owner)
    )


async def load_task_for_suite(
    session: AsyncSession,
    suite_id: str,
    actor: str | None,
) -> Task:
    """Load parent Task for a test suite; enforce ownership."""
    result = await session.execute(
        select(Task)
        .join(TestSuite, TestSuite.task_id == Task.id)
        .where(TestSuite.id == suite_id)
    )
    task = result.scalar_one_or_none()
    if task is None or not can_access_task(task, actor):
        raise NotFoundError("测试用例", suite_id)
    return task


async def load_trace_with_access(
    session: AsyncSession,
    trace_id: str,
    actor: str | None,
    *,
    with_scores: bool = True,
) -> Trace:
    """Load a Trace and ensure the caller owns the parent Task."""
    opts = [selectinload(Trace.metric_scores)] if with_scores else []
    result = await session.execute(
        select(Trace).options(*opts).where(Trace.id == trace_id)
    )
    trace = result.scalar_one_or_none()
    if trace is None:
        raise NotFoundError("执行轨迹", trace_id)

    # Resolve parent task via suite
    suite_result = await session.execute(
        select(TestSuite).where(TestSuite.id == trace.test_suite_id)
    )
    suite = suite_result.scalar_one_or_none()
    if suite is None:
        raise NotFoundError("执行轨迹", trace_id)

    task_result = await session.execute(select(Task).where(Task.id == suite.task_id))
    task = task_result.scalar_one_or_none()
    if task is None or not can_access_task(task, actor):
        # Hide existence of foreign traces
        raise NotFoundError("执行轨迹", trace_id)
    return trace
