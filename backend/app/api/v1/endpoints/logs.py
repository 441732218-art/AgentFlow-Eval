# (c) 2026 AgentFlow-Eval
"""AOLS log query API — list + statistics for Dashboard / Monitoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.rbac import Permission, require_permission
from app.models.agent_log import AgentLog

router = APIRouter()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Support Z suffix
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _row_to_dict(row: AgentLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "level": row.level,
        "event": row.event,
        "service": row.service,
        "trace_id": row.trace_id,
        "task_id": row.task_id,
        "payload": row.payload or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
@require_permission(Permission.EVALUATION_READ)
async def list_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: str | None = Query(None, description="info|warning|error|debug"),
    event: str | None = Query(None, description="exact or prefix e.g. llm."),
    task_id: str | None = None,
    trace_id: str | None = None,
    since: str | None = Query(None, description="ISO datetime"),
    until: str | None = Query(None, description="ISO datetime"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Paginated structured logs from ``agent_logs``."""
    # Ensure pending sink rows are visible (best-effort)
    try:
        from app.core.observability.aols.sinks.db import flush_agent_logs_sync

        flush_agent_logs_sync()
    except Exception:
        pass

    q = select(AgentLog)
    count_q = select(func.count(AgentLog.id))

    if level:
        q = q.where(AgentLog.level == level.lower())
        count_q = count_q.where(AgentLog.level == level.lower())
    if event:
        if event.endswith("."):
            q = q.where(AgentLog.event.startswith(event))
            count_q = count_q.where(AgentLog.event.startswith(event))
        elif "*" in event:
            like = event.replace("*", "%")
            q = q.where(AgentLog.event.like(like))
            count_q = count_q.where(AgentLog.event.like(like))
        else:
            q = q.where(AgentLog.event == event)
            count_q = count_q.where(AgentLog.event == event)
    if task_id:
        q = q.where(AgentLog.task_id == task_id)
        count_q = count_q.where(AgentLog.task_id == task_id)
    if trace_id:
        q = q.where(AgentLog.trace_id == trace_id)
        count_q = count_q.where(AgentLog.trace_id == trace_id)

    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)
    if since_dt:
        q = q.where(AgentLog.created_at >= since_dt)
        count_q = count_q.where(AgentLog.created_at >= since_dt)
    if until_dt:
        q = q.where(AgentLog.created_at <= until_dt)
        count_q = count_q.where(AgentLog.created_at <= until_dt)

    try:
        total = int((await session.execute(count_q)).scalar() or 0)
        q = (
            q.order_by(AgentLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await session.execute(q)).scalars().all())
    except Exception:
        # Table may not exist yet during migration window
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "note": "agent_logs unavailable",
        }

    return {
        "items": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/statistics")
@require_permission(Permission.EVALUATION_READ)
async def log_statistics(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Aggregate log-derived KPIs for Dashboard charts."""
    try:
        from app.core.observability.aols.sinks.db import flush_agent_logs_sync

        flush_agent_logs_sync()
    except Exception:
        pass

    since = datetime.now(timezone.utc) - timedelta(days=days)
    empty = {
        "window_days": days,
        "since": since.isoformat(),
        "error_count": 0,
        "total_events": 0,
        "agent_failure_rate": None,
        "agent_failed": 0,
        "agent_completed": 0,
        "by_event": {},
        "token_trend": [],
        "latency_trend": [],
        "error_trend": [],
    }

    try:
        # Error counts
        err_q = select(func.count(AgentLog.id)).where(
            AgentLog.created_at >= since,
            AgentLog.level.in_(["error", "warning"]),
        )
        error_count = int((await session.execute(err_q)).scalar() or 0)
    except Exception:
        return empty

    total_q = select(func.count(AgentLog.id)).where(AgentLog.created_at >= since)
    total_events = int((await session.execute(total_q)).scalar() or 0)

    # Agent failure rate: agent.failed / (agent.completed + agent.failed)
    failed_agents = int(
        (
            await session.execute(
                select(func.count(AgentLog.id)).where(
                    AgentLog.created_at >= since,
                    AgentLog.event == "agent.failed",
                )
            )
        ).scalar()
        or 0
    )
    completed_agents = int(
        (
            await session.execute(
                select(func.count(AgentLog.id)).where(
                    AgentLog.created_at >= since,
                    AgentLog.event == "agent.completed",
                )
            )
        ).scalar()
        or 0
    )
    agent_den = failed_agents + completed_agents
    agent_failure_rate = round(failed_agents / agent_den, 4) if agent_den else None

    # By event top
    by_event_rows = (
        await session.execute(
            select(AgentLog.event, func.count(AgentLog.id))
            .where(AgentLog.created_at >= since)
            .group_by(AgentLog.event)
            .order_by(func.count(AgentLog.id).desc())
            .limit(20)
        )
    ).all()
    by_event = {str(e): int(c) for e, c in by_event_rows}

    # Daily trends from payload fields (best-effort)
    # Pull recent llm.completed / tool / evaluation rows and bucket by day
    day_list = [
        (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()
        for i in range(days)
    ]
    labels = [d.strftime("%m-%d") for d in day_list]
    token_map: dict[str, float] = {lab: 0.0 for lab in labels}
    latency_map: dict[str, list[float]] = {lab: [] for lab in labels}
    error_map: dict[str, int] = {lab: 0 for lab in labels}

    recent = list(
        (
            await session.execute(
                select(AgentLog)
                .where(AgentLog.created_at >= since)
                .order_by(AgentLog.created_at.asc())
                .limit(5000)
            )
        )
        .scalars()
        .all()
    )
    for row in recent:
        lab = row.created_at.strftime("%m-%d") if row.created_at else None
        if not lab or lab not in token_map:
            continue
        pl = row.payload or {}
        if row.level in {"error", "warning"} or row.event.endswith(".failed"):
            error_map[lab] = error_map.get(lab, 0) + 1
        tok = pl.get("total_tokens")
        if tok is None and isinstance(pl.get("payload"), dict):
            tok = pl["payload"].get("total_tokens")
        if tok is not None:
            try:
                token_map[lab] += float(tok)
            except (TypeError, ValueError):
                pass
        lat = pl.get("latency_ms") or pl.get("duration_ms")
        if lat is not None:
            try:
                latency_map[lab].append(float(lat))
            except (TypeError, ValueError):
                pass

    token_trend = [{"t": lab, "v": int(token_map[lab])} for lab in labels]
    latency_trend = [
        {
            "t": lab,
            "v": round(sum(latency_map[lab]) / len(latency_map[lab]), 1)
            if latency_map[lab]
            else 0,
        }
        for lab in labels
    ]
    error_trend = [{"t": lab, "v": error_map[lab]} for lab in labels]

    return {
        "window_days": days,
        "since": since.isoformat(),
        "error_count": error_count,
        "total_events": total_events,
        "agent_failure_rate": agent_failure_rate,
        "agent_failed": failed_agents,
        "agent_completed": completed_agents,
        "by_event": by_event,
        "token_trend": token_trend,
        "latency_trend": latency_trend,
        "error_trend": error_trend,
    }
