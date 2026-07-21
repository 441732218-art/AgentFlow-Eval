# (c) 2026 AgentFlow-Eval
"""Benchmark platform API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.benchmark.service import get_benchmark_service
from app.core.dependencies import get_db
from app.core.rbac import Permission, require_permission
from app.core.tenant_context import (
    current_tenant_id,
    extract_tenant_header,
    resolve_tenant_context,
)
from app.utils.exceptions import AgentFlowError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


async def _bind_tenant(request: Request, session: AsyncSession) -> str | None:
    role = getattr(request.state, "role", None)
    role_s = role.value if hasattr(role, "value") else str(role or "")
    await resolve_tenant_context(
        session,
        actor=_actor(request),
        header_value=extract_tenant_header(request),
        system_role=role_s,
    )
    return current_tenant_id()


class BenchmarkCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    cases: list[dict[str, Any]] = Field(default_factory=list)
    version: str = Field(default="1.0", max_length=64)
    scorecard: dict[str, Any] | None = Field(
        default=None, description="Optional Scorecard JSON (Phase 3)"
    )
    source_task_id: str | None = Field(
        default=None, description="If set, clone suites from this Task as cases"
    )


class BenchmarkRunBody(BaseModel):
    label: str = "default"
    agent_config: dict[str, Any] = Field(
        default_factory=lambda: {
            "runner": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0,
        }
    )
    enqueue: bool = True


class ImportBody(BaseModel):
    format: str = Field("json", description="json | csv")
    content: str = Field(..., min_length=1)


class CompareRunsBody(BaseModel):
    """Compare current run against a baseline (defaults to previous completed run)."""

    current_run_id: str
    baseline_run_id: str | None = Field(
        default=None,
        description="If omitted, use the previous completed run before current",
    )
    score_stable_eps: float = Field(
        default=1.0, ge=0, description="|Δscore| below this → stable"
    )


def _bm_dict(bm, *, case_count: int | None = None) -> dict[str, Any]:
    meta = dict(bm.meta or {})
    return {
        "id": bm.id,
        "name": bm.name,
        "description": bm.description,
        "status": bm.status,
        "created_by": bm.created_by,
        "tags": bm.tags or [],
        "tenant_id": bm.tenant_id,
        "version": meta.get("version") or "1.0",
        "scorecard": meta.get("scorecard"),
        "source_task_id": meta.get("source_task_id"),
        "case_count": case_count
        if case_count is not None
        else (len(bm.cases) if getattr(bm, "cases", None) is not None else None),
        "created_at": bm.created_at.isoformat() if bm.created_at else None,
    }


def _run_dict(run) -> dict[str, Any]:
    return {
        "id": run.id,
        "benchmark_id": run.benchmark_id,
        "task_id": run.task_id,
        "label": run.label,
        "status": run.status,
        "agent_config": run.agent_config or {},
        "summary": run.summary or {},
        "created_by": run.created_by,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("")
@require_permission(Permission.BENCHMARK_READ, Permission.TASK_READ, require_all=False)
async def list_benchmarks(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tenant_id = await _bind_tenant(request, session)
    svc = get_benchmark_service()
    items = await svc.list_benchmarks(
        session, actor=_actor(request), tenant_id=tenant_id, limit=limit
    )
    out = []
    for bm in items:
        full = await svc.get_benchmark(session, bm.id, with_cases=True)
        out.append(_bm_dict(full, case_count=len(full.cases)))
    return {"items": out, "total": len(out)}


@router.post("", status_code=201)
@require_permission(
    Permission.BENCHMARK_CREATE, Permission.TASK_CREATE, require_all=False
)
async def create_benchmark(
    body: BenchmarkCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tenant_id = await _bind_tenant(request, session)
    svc = get_benchmark_service()
    if body.source_task_id:
        bm = await svc.create_from_task(
            session,
            task_id=body.source_task_id,
            name=body.name,
            description=body.description,
            version=body.version,
            created_by=_actor(request),
            tenant_id=tenant_id,
            scorecard=body.scorecard,
        )
        if body.cases:
            await svc.add_cases(
                session, bm, body.cases, tenant_id=tenant_id
            )
    else:
        bm = await svc.create_benchmark(
            session,
            name=body.name,
            description=body.description,
            created_by=_actor(request),
            tenant_id=tenant_id,
            tags=body.tags,
            cases=body.cases,
            version=body.version,
            scorecard=body.scorecard,
        )
    await session.commit()
    full = await svc.get_benchmark(session, bm.id, with_cases=True)
    return {
        **_bm_dict(full, case_count=len(full.cases)),
        "cases": [
            {
                "id": c.id,
                "name": c.name,
                "user_query": c.user_query,
                "expected_output": c.expected_output,
                "expected_tools": c.expected_tools,
                "weight": c.weight,
            }
            for c in full.cases
        ],
    }


@router.get("/{benchmark_id}")
@require_permission(Permission.BENCHMARK_READ, Permission.TASK_READ, require_all=False)
async def get_benchmark(
    benchmark_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _bind_tenant(request, session)
    svc = get_benchmark_service()
    bm = await svc.get_benchmark(session, benchmark_id, with_cases=True)
    return {
        **_bm_dict(bm, case_count=len(bm.cases)),
        "cases": [
            {
                "id": c.id,
                "name": c.name,
                "user_query": c.user_query,
                "expected_output": c.expected_output,
                "expected_tools": c.expected_tools,
                "weight": c.weight,
            }
            for c in bm.cases
        ],
    }


@router.post("/{benchmark_id}/import")
@require_permission(
    Permission.BENCHMARK_CREATE, Permission.TASK_CREATE, require_all=False
)
async def import_cases(
    benchmark_id: str,
    body: ImportBody,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tenant_id = await _bind_tenant(request, session)
    svc = get_benchmark_service()
    bm = await svc.get_benchmark(session, benchmark_id, with_cases=False)
    try:
        cases = svc.parse_import_payload(content=body.content, fmt=body.format)
    except AgentFlowError:
        raise
    except Exception as exc:
        raise AgentFlowError(f"import parse failed: {exc}", status_code=422) from exc
    created = await svc.add_cases(session, bm, cases, tenant_id=tenant_id)
    await session.commit()
    return {"imported": len(created), "benchmark_id": bm.id}


@router.post("/{benchmark_id}/import/file")
@require_permission(
    Permission.BENCHMARK_CREATE, Permission.TASK_CREATE, require_all=False
)
async def import_cases_file(
    benchmark_id: str,
    request: Request,
    file: UploadFile = File(...),
    format: str = Query("json", description="json | csv"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tenant_id = await _bind_tenant(request, session)
    raw = await file.read()
    content = raw.decode("utf-8", errors="replace")
    name = (file.filename or "").lower()
    fmt = format
    if name.endswith(".csv"):
        fmt = "csv"
    elif name.endswith(".json"):
        fmt = "json"
    svc = get_benchmark_service()
    bm = await svc.get_benchmark(session, benchmark_id, with_cases=False)
    cases = svc.parse_import_payload(content=content, fmt=fmt)
    created = await svc.add_cases(session, bm, cases, tenant_id=tenant_id)
    await session.commit()
    return {"imported": len(created), "benchmark_id": bm.id, "format": fmt}


@router.post("/{benchmark_id}/run", status_code=201)
@require_permission(
    Permission.BENCHMARK_CREATE, Permission.TASK_EXECUTE, require_all=False
)
async def run_benchmark(
    benchmark_id: str,
    body: BenchmarkRunBody,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run benchmark through Evaluation Engine (creates Task + enqueues)."""
    tenant_id = await _bind_tenant(request, session)
    svc = get_benchmark_service()
    try:
        run = await svc.run_benchmark(
            session,
            benchmark_id=benchmark_id,
            actor=_actor(request),
            agent_config=body.agent_config,
            label=body.label,
            tenant_id=tenant_id,
            enqueue=body.enqueue,
        )
    except AgentFlowError:
        raise
    await session.commit()
    return {"run": _run_dict(run)}


@router.get("/{benchmark_id}/runs")
@require_permission(Permission.BENCHMARK_READ, Permission.TASK_READ, require_all=False)
async def list_runs(
    benchmark_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """History of regression evaluation runs for continuous evaluation."""
    await _bind_tenant(request, session)
    svc = get_benchmark_service()
    runs = await svc.list_runs(session, benchmark_id, limit=limit)
    await session.commit()
    return {
        "benchmark_id": benchmark_id,
        "items": [_run_dict(r) for r in runs],
        "total": len(runs),
    }


@router.post("/{benchmark_id}/runs/{run_id}/finalize")
@require_permission(Permission.BENCHMARK_READ, Permission.TASK_READ, require_all=False)
async def finalize_run(
    benchmark_id: str,
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _bind_tenant(request, session)
    svc = get_benchmark_service()
    run = await svc.finalize_run(session, run_id)
    if run.benchmark_id != benchmark_id:
        raise AgentFlowError("Run does not belong to benchmark", status_code=400)
    await session.commit()
    return {"run": _run_dict(run)}


@router.post("/{benchmark_id}/compare")
@require_permission(Permission.BENCHMARK_READ, Permission.TASK_READ, require_all=False)
async def compare_runs(
    benchmark_id: str,
    body: CompareRunsBody,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compare two runs (or current vs previous) for regression detection."""
    await _bind_tenant(request, session)
    svc = get_benchmark_service()
    await svc.get_benchmark(session, benchmark_id, with_cases=False)

    current = await svc.get_run(session, body.current_run_id)
    if current.benchmark_id != benchmark_id:
        raise AgentFlowError("current_run_id not in this benchmark", status_code=400)

    if body.baseline_run_id:
        baseline = await svc.get_run(session, body.baseline_run_id)
        if baseline.benchmark_id != benchmark_id:
            raise AgentFlowError(
                "baseline_run_id not in this benchmark", status_code=400
            )
    else:
        # Previous completed run before current (by created_at)
        history = await svc.list_runs(session, benchmark_id, limit=100)
        baseline = None
        for r in history:
            if r.id == current.id:
                continue
            if r.created_at and current.created_at and r.created_at >= current.created_at:
                continue
            if r.status == "completed" or (r.summary or {}).get("score") is not None:
                baseline = r
                break
        if baseline is None:
            raise AgentFlowError(
                "No baseline run found — provide baseline_run_id or complete a prior run",
                status_code=400,
            )

    result = svc.compare_runs(
        current, baseline, score_stable_eps=body.score_stable_eps
    )
    await session.commit()
    return {"benchmark_id": benchmark_id, **result}


@router.get("/{benchmark_id}/leaderboard")
@require_permission(Permission.BENCHMARK_READ, Permission.TASK_READ, require_all=False)
async def leaderboard(
    benchmark_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _bind_tenant(request, session)
    svc = get_benchmark_service()
    # ensure benchmark exists
    await svc.get_benchmark(session, benchmark_id, with_cases=False)
    board = await svc.leaderboard(session, benchmark_id)
    await session.commit()
    return {
        "benchmark_id": benchmark_id,
        "items": board,
        "total": len(board),
        "metrics": [
            "score",
            "success_rate",
            "score_coverage",
            "accuracy",
            "quality",
            "latency_ms",
            "cost",
            "tokens",
        ],
    }
