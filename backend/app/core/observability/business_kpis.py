# (c) 2026 AgentFlow-Eval
"""Business KPI aggregation from ORM tables (read-only)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.trace import Trace


async def compute_kpis(
    session: AsyncSession,
    *,
    days: int = 7,
    actor: str | None = None,
) -> dict[str, Any]:
    """Aggregate task success rate, avg score, token-ish totals, latency proxy."""
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))

    # Status counts
    status_q = (
        select(Task.status, func.count())
        .where(Task.created_at >= since)
        .group_by(Task.status)
    )
    if actor and actor not in {"admin", "anonymous", "public"}:
        status_q = status_q.where(Task.created_by == actor)
    rows = await session.execute(status_q)
    by_status: dict[str, int] = {}
    total = 0
    for st, cnt in rows.all():
        key = st.value if hasattr(st, "value") else str(st)
        by_status[key] = int(cnt)
        total += int(cnt)

    completed = by_status.get(TaskStatus.COMPLETED.value, 0)
    failed = by_status.get(TaskStatus.FAILED.value, 0) + by_status.get(
        TaskStatus.TIMEOUT.value, 0
    )
    terminal = completed + failed
    success_rate = (completed / terminal) if terminal else None

    # Avg metric score
    score_q = select(func.avg(MetricScore.score)).select_from(MetricScore)
    # join traces created recently if possible
    try:
        score_q = (
            select(func.avg(MetricScore.score))
            .select_from(MetricScore)
            .join(Trace, Trace.id == MetricScore.trace_id)
            .where(Trace.created_at >= since)
        )
    except Exception:
        pass
    avg_score_row = await session.execute(score_q)
    avg_score = avg_score_row.scalar()
    avg_score_f = float(avg_score) if avg_score is not None else None

    # Token sum from traces
    tok_q = select(func.coalesce(func.sum(Trace.total_tokens), 0)).where(
        Trace.created_at >= since
    )
    tokens = int((await session.execute(tok_q)).scalar() or 0)

    # Latency proxy: avg response_time_ms
    lat_q = select(func.avg(Trace.response_time_ms)).where(
        Trace.created_at >= since,
        Trace.response_time_ms.isnot(None),
    )
    avg_ms = (await session.execute(lat_q)).scalar()
    avg_latency_ms = float(avg_ms) if avg_ms is not None else None

    # Error topology by task status (stage approximation)
    error_topology = {
        "task_failed": by_status.get("failed", 0),
        "task_timeout": by_status.get("timeout", 0),
        "task_cancelled": by_status.get("cancelled", 0),
        "task_running": by_status.get("running", 0) + by_status.get("queued", 0),
    }

    return {
        "window_days": days,
        "since": since.isoformat(),
        "tasks_total": total,
        "by_status": by_status,
        "success_rate": round(success_rate, 4) if success_rate is not None else None,
        "avg_metric_score": round(avg_score_f, 4) if avg_score_f is not None else None,
        "total_tokens": tokens,
        "avg_trace_latency_ms": (
            round(avg_latency_ms, 2) if avg_latency_ms is not None else None
        ),
        "error_topology": error_topology,
    }
