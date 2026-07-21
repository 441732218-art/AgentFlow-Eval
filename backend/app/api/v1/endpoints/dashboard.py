# (c) 2026 AgentFlow-Eval
"""Dashboard stats API with short-TTL cache + Intelligence Center overview."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.rbac import Permission, get_request_role, require_permission

router = APIRouter()


@router.get("/stats")
@require_permission(Permission.TASK_READ)
async def dashboard_stats(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return aggregated task counts for the current actor (cached 1 min)."""
    from app.core.cache.services import get_cached_dashboard

    actor = getattr(request.state, "actor", None) or "anonymous"
    role = get_request_role(request).value
    return await get_cached_dashboard(session, actor=actor, role=role)


def _build_topology(
    *,
    running: int,
    completed: int,
    failed: int,
    avg_score: float | None,
    latency_ms: float | None,
    tokens: int,
    success_rate: float | None,
    model_hint: str | None = None,
) -> dict[str, Any]:
    """Horizontal ReAct pipeline topology for ReactFlow cockpit."""
    tool_status = (
        "error" if failed > max(completed, 1) else ("warn" if failed else "ok")
    )
    planner_status = "ok" if running or completed else "idle"
    if running:
        planner_status = "ok"
    judge_status = "ok" if completed else ("warn" if failed else "idle")
    observe_status = "warn" if failed else "ok"

    lat_label = f"{round(latency_ms)} ms" if latency_ms is not None else "—"
    score_label = f"{avg_score:.1f}" if avg_score is not None else "—"
    sr = f"{success_rate * 100:.1f}%" if success_rate is not None else "—"

    nodes = [
        {
            "id": "user",
            "label": "User Request",
            "status": "ok",
            "kind": "ingress",
            "meta": {
                "type": "ingress",
                "input": "Business query / test suite",
                "output": "→ Planner",
                "latency": "< 1 ms",
                "model": "—",
            },
        },
        {
            "id": "planner",
            "label": "Planner Agent",
            "status": planner_status,
            "kind": "agent",
            "meta": {
                "type": "agent",
                "running": running,
                "input": "User query + system prompt",
                "output": "Thought / plan / tool plan",
                "token": tokens // max(running + completed, 1) if tokens else 0,
                "latency": lat_label,
                "model": model_hint or "openai-compatible",
            },
        },
        {
            "id": "tool",
            "label": "Tool Calling",
            "status": tool_status,
            "kind": "tool",
            "meta": {
                "type": "tool",
                "failed": failed,
                "input": "Function call args",
                "output": "Tool observation payload",
                "latency": "sandbox",
                "error": f"{failed} failed tasks" if failed else "",
            },
        },
        {
            "id": "observe",
            "label": "Observation",
            "status": observe_status,
            "kind": "observe",
            "meta": {
                "type": "observe",
                "input": "Tool result",
                "output": "Normalized observation",
                "latency": lat_label,
            },
        },
        {
            "id": "judge",
            "label": "LLM Judge",
            "status": judge_status,
            "kind": "judge",
            "meta": {
                "type": "judge",
                "score": avg_score,
                "input": "Trace + expected",
                "output": f"Score {score_label} · SR {sr}",
                "latency": lat_label,
                "model": "judge-engine",
            },
        },
    ]

    edges = [
        {"source": "user", "target": "planner", "label": "dispatch"},
        {"source": "planner", "target": "tool", "label": "act"},
        {"source": "tool", "target": "observe", "label": "result"},
        {"source": "observe", "target": "judge", "label": "score"},
    ]
    # Feedback loop when failures present (visual diagnosis hook)
    if failed:
        edges.append(
            {
                "source": "observe",
                "target": "planner",
                "type": "loop",
                "label": "retry",
            }
        )

    return {
        "layout": "horizontal",
        "nodes": nodes,
        "edges": edges,
        "legend": [
            {"status": "ok", "label": "Healthy"},
            {"status": "warn", "label": "Degraded"},
            {"status": "error", "label": "Failure"},
            {"status": "idle", "label": "Idle"},
        ],
    }


@router.get("")
@router.get("/overview")
@require_permission(Permission.TASK_READ)
async def dashboard_overview(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Intelligence Center cockpit payload for ECharts + ReactFlow."""
    from app.core.cache.services import get_cached_dashboard
    from app.core.observability.business_kpis import compute_kpis
    from app.core.observability.timeseries import compute_dashboard_series

    actor = getattr(request.state, "actor", None) or "anonymous"
    role = get_request_role(request).value
    stats = await get_cached_dashboard(session, actor=actor, role=role)
    kpis = await compute_kpis(session, days=days, actor=actor)
    series = await compute_dashboard_series(session, days=days, actor=actor)

    by = stats.get("tasks_by_status") or {}
    running = int(
        stats.get("active_tasks")
        or (
            by.get("running", 0)
            + by.get("queued", 0)
            + by.get("judging", 0)
            + by.get("waiting_tool", 0)
        )
    )
    completed = int(stats.get("completed_tasks") or by.get("completed") or 0)
    failed = int(
        stats.get("failed_tasks") or (by.get("failed", 0) + by.get("timeout", 0))
    )
    total = int(stats.get("tasks_total") or 0)
    terminal = completed + failed

    success_rate = kpis.get("success_rate")
    if success_rate is None and terminal:
        success_rate = completed / terminal
    failure_rate = None
    if success_rate is not None:
        failure_rate = round(1.0 - float(success_rate), 4)
    elif terminal:
        failure_rate = round(failed / terminal, 4)

    latency_ms = kpis.get("avg_trace_latency_ms")
    tokens = int(kpis.get("total_tokens") or 0)
    avg_score = kpis.get("avg_metric_score")

    health = 99.0
    if success_rate is not None:
        health = min(100.0, max(0.0, float(success_rate) * 100.0))
    if latency_ms is not None and latency_ms > 3000:
        health = max(0.0, health - min(15.0, (latency_ms - 3000) / 500))
    if failed and total:
        health = max(0.0, health - min(20.0, (failed / max(total, 1)) * 40))
    if avg_score is not None and avg_score < 60:
        health = max(0.0, health - (60 - avg_score) * 0.3)

    status_distribution = [
        {"name": k, "value": int(v)} for k, v in sorted(by.items()) if int(v) > 0
    ]

    topology = _build_topology(
        running=running,
        completed=completed,
        failed=failed,
        avg_score=float(avg_score) if avg_score is not None else None,
        latency_ms=float(latency_ms) if latency_ms is not None else None,
        tokens=tokens,
        success_rate=float(success_rate) if success_rate is not None else None,
    )

    error_topology = kpis.get("error_topology") or {}

    return {
        "health": round(health, 1),
        "agents": running,
        "success_rate": (
            round(float(success_rate), 4) if success_rate is not None else None
        ),
        "failure_rate": failure_rate,
        "latency": (
            round(float(latency_ms) / 1000.0, 3) if latency_ms is not None else None
        ),
        "latency_ms": latency_ms,
        "tokens": tokens,
        "cost": None,
        "avg_score": avg_score,
        "stats": stats,
        "kpis": kpis,
        "series": {
            "agents": series.get("agents", []),
            "tokens": series.get("tokens", []),
            "latency": series.get("latency", []),
            "errors": series.get("errors", []),
            "success_rate": series.get("success_rate", []),
        },
        "series_meta": {
            "source": series.get("source", "orm"),
            "days": days,
        },
        "status_distribution": status_distribution,
        "error_topology": [
            {"name": k, "value": int(v)}
            for k, v in error_topology.items()
            if int(v or 0) > 0
        ],
        "topology": topology,
        "window_days": days,
    }
