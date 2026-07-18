# (c) 2026 AgentFlow-Eval
"""Daily timeseries aggregation for Intelligence Center dashboard charts."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace, TraceStatus


def _day_labels(days: int, end: date | None = None) -> list[date]:
    end = end or datetime.now(timezone.utc).date()
    return [end - timedelta(days=days - 1 - i) for i in range(days)]


def _label(d: date) -> str:
    return d.strftime("%m-%d")


async def compute_dashboard_series(
    session: AsyncSession,
    *,
    days: int = 7,
    actor: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Aggregate per-day agents(tasks active), tokens, latency, errors from ORM.

    Returns series keys: agents, tokens, latency, errors, success_rate (0-100).
    Missing days are zero-filled for stable ECharts categories.
    """
    days = max(1, min(int(days), 90))
    day_list = _day_labels(days)
    since = datetime.combine(day_list[0], datetime.min.time(), tzinfo=timezone.utc)

    # ---- Traces: tokens, latency, errors by day ----
    # SQLite: date(created_at); Postgres: cast/date_trunc — use func.date for portability
    day_expr = func.date(Trace.created_at)

    trace_q = (
        select(
            day_expr.label("d"),
            func.count(Trace.id).label("n"),
            func.coalesce(func.sum(Trace.total_tokens), 0).label("tokens"),
            func.avg(Trace.response_time_ms).label("avg_lat"),
            func.sum(
                case((Trace.status == TraceStatus.FAILED, 1), else_=0)
            ).label("errors"),
            func.sum(
                case((Trace.status == TraceStatus.SUCCESS, 1), else_=0)
            ).label("ok"),
        )
        .where(Trace.created_at >= since)
        .group_by(day_expr)
    )

    # Optional tenancy: traces owned via suite → task.created_by
    if actor and actor not in {"admin", "anonymous", "public"}:
        trace_q = (
            trace_q.join(TestSuite, TestSuite.id == Trace.test_suite_id)
            .join(Task, Task.id == TestSuite.task_id)
            .where(Task.created_by == actor)
        )

    rows = (await session.execute(trace_q)).all()
    by_day: dict[str, dict[str, float]] = {}
    for r in rows:
        raw = r.d
        if raw is None:
            continue
        if isinstance(raw, datetime):
            key = raw.date().isoformat()
        elif isinstance(raw, date):
            key = raw.isoformat()
        else:
            key = str(raw)[:10]
        by_day[key] = {
            "tokens": float(r.tokens or 0),
            "latency": float(r.avg_lat or 0),
            "errors": float(r.errors or 0),
            "ok": float(r.ok or 0),
            "n": float(r.n or 0),
        }

    # ---- Tasks created / terminal failed by day (agents proxy) ----
    tday = func.date(Task.created_at)
    task_q = (
        select(
            tday.label("d"),
            func.count(Task.id).label("n"),
            func.sum(
                case(
                    (
                        Task.status.in_(
                            [
                                TaskStatus.RUNNING,
                                TaskStatus.QUEUED,
                                TaskStatus.JUDGING,
                                TaskStatus.WAITING_TOOL,
                            ]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("active"),
            func.sum(
                case(
                    (Task.status.in_([TaskStatus.FAILED, TaskStatus.TIMEOUT]), 1),
                    else_=0,
                )
            ).label("failed"),
        )
        .where(Task.created_at >= since)
        .group_by(tday)
    )
    if actor and actor not in {"admin", "anonymous", "public"}:
        task_q = task_q.where(Task.created_by == actor)

    task_rows = (await session.execute(task_q)).all()
    task_by: dict[str, dict[str, float]] = {}
    for r in task_rows:
        raw = r.d
        if raw is None:
            continue
        if isinstance(raw, datetime):
            key = raw.date().isoformat()
        elif isinstance(raw, date):
            key = raw.isoformat()
        else:
            key = str(raw)[:10]
        task_by[key] = {
            "n": float(r.n or 0),
            "active": float(r.active or 0),
            "failed": float(r.failed or 0),
        }

    agents: list[dict[str, Any]] = []
    tokens: list[dict[str, Any]] = []
    latency: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    success_rate: list[dict[str, Any]] = []

    for d in day_list:
        iso = d.isoformat()
        lab = _label(d)
        tr = by_day.get(iso, {})
        tk = task_by.get(iso, {})
        n_tr = tr.get("n", 0)
        ok = tr.get("ok", 0)
        rate = round((ok / n_tr) * 100, 1) if n_tr else 0.0

        agents.append({"t": lab, "v": int(tk.get("n", 0) or tr.get("n", 0))})
        tokens.append({"t": lab, "v": int(tr.get("tokens", 0))})
        latency.append({"t": lab, "v": round(tr.get("latency", 0), 1)})
        errors.append(
            {
                "t": lab,
                "v": int(tr.get("errors", 0) + tk.get("failed", 0)),
            }
        )
        success_rate.append({"t": lab, "v": rate})

    return {
        "agents": agents,
        "tokens": tokens,
        "latency": latency,
        "errors": errors,
        "success_rate": success_rate,
        "source": "orm",
    }
