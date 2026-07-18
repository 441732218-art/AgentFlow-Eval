# (c) 2026 AgentFlow-Eval
"""Business KPIs, slow tasks, error topology (read-only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_db
from app.core.observability.business_kpis import compute_kpis
from app.core.observability.slow_tasks import list_slow_tasks, list_slow_tasks_db
from app.core.observability.tracing import get_trace_id
from app.core.profiles import profile_status
from app.core.rbac import Permission, require_permission

router = APIRouter()


@router.get("/kpis")
@require_permission(Permission.TASK_READ)
async def get_kpis(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Business KPI dashboard data."""
    if not getattr(settings, "OBSERVABILITY_KPI_ENABLED", True):
        return {"enabled": False, "items": {}}
    actor = getattr(request.state, "actor", None)
    data = await compute_kpis(session, days=days, actor=None)
    return {
        "enabled": True,
        "kpis": data,
        "deploy": profile_status(),
        "viewer": actor,
        "trace_id": getattr(request.state, "request_id", None) or get_trace_id() or None,
    }


@router.get("/slow-tasks")
@require_permission(Permission.TASK_READ)
async def get_slow_tasks(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    source: str = Query(
        "auto",
        description="auto|db|memory — auto prefers durable DB with memory fallback",
    ),
) -> dict[str, Any]:
    """Recent suite/judge runs exceeding SLOW_TASK_THRESHOLD_SEC."""
    src = (source or "auto").lower().strip()
    if src == "memory":
        items = list_slow_tasks(limit=limit)
        for it in items:
            it.setdefault("source", "memory")
        used = "memory"
    elif src == "db":
        items = await list_slow_tasks_db(limit=limit)
        used = "db"
    else:
        items = await list_slow_tasks_db(limit=limit)
        used = "db" if items and items[0].get("source") == "db" else "memory"
        if not items:
            items = list_slow_tasks(limit=limit)
            for it in items:
                it.setdefault("source", "memory")
            used = "memory" if items else used
    return {
        "items": items,
        "total": len(items),
        "source": used,
        "threshold_sec": float(
            getattr(settings, "SLOW_TASK_THRESHOLD_SEC", 30.0) or 30.0
        ),
        "trace_id": getattr(request.state, "request_id", None) or get_trace_id() or None,
    }


@router.get("/error-topology")
@require_permission(Permission.TASK_READ)
async def get_error_topology(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    data = await compute_kpis(session, days=days)
    return {
        "window_days": days,
        "topology": data.get("error_topology") or {},
        "by_status": data.get("by_status") or {},
    }
