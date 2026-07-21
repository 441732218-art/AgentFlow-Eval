# (c) 2026 AgentFlow-Eval
"""Optimized query helpers — avoid N+1 patterns on hot list endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.test_suite import TestSuite


async def batch_suite_counts(
    session: AsyncSession,
    task_ids: Sequence[str],
) -> dict[str, int]:
    """Return ``{task_id: suite_count}`` in a single grouped query.

    Args:
        session: Async DB session.
        task_ids: Task primary keys (empty → empty dict).

    Returns:
        Mapping of task_id to number of test suites. Missing ids map to 0
        when looked up via ``.get(id, 0)``.
    """
    if not task_ids:
        return {}
    # Deduplicate while preserving order for stable tests
    unique_ids = list(dict.fromkeys(task_ids))
    result = await session.execute(
        select(TestSuite.task_id, func.count(TestSuite.id))
        .where(TestSuite.task_id.in_(unique_ids))
        .group_by(TestSuite.task_id)
    )
    return {str(row[0]): int(row[1]) for row in result.all()}


async def count_suites_for_task(session: AsyncSession, task_id: str) -> int:
    """Count suites for one task (detail views)."""
    result = await session.execute(
        select(func.count(TestSuite.id)).where(TestSuite.task_id == task_id)
    )
    return int(result.scalar() or 0)


async def tasks_with_suite_counts(
    session: AsyncSession,
    tasks: Sequence[Task],
) -> list[tuple[Task, int]]:
    """Attach suite counts to a page of tasks without N+1 queries.

    Args:
        session: Async DB session.
        tasks: Already-fetched Task rows (e.g. one list page).

    Returns:
        List of ``(task, suite_count)`` in the same order as ``tasks``.
    """
    counts = await batch_suite_counts(session, [t.id for t in tasks])
    return [(t, counts.get(t.id, 0)) for t in tasks]


def apply_task_list_filters(
    query: Select[Any],
    *,
    status: str | None = None,
    include_archived: bool = False,
) -> Select[Any]:
    """Apply common list filters used by ``GET /tasks``."""
    if not include_archived:
        query = query.where(Task.is_archived.is_(False))
    if status:
        query = query.where(Task.status == status)
    return query
