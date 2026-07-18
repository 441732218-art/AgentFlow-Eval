# (c) 2026 AgentFlow-Eval
"""Online A/B testing REST API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ab import service as ab_service
from app.core.ab.service import utcnow
from app.core.audit import write_audit
from app.core.dependencies import get_db
from app.core.rbac import Permission, require_permission
from app.models.ab_test import ABExperiment, ABStatus, ABVariant
from app.schemas.ab_test import (
    ABAssignRequest,
    ABAssignResponse,
    ABExperimentCreate,
    ABExperimentListResponse,
    ABExperimentResponse,
    ABSampleSizeRequest,
    ABStatusUpdate,
    ABTrackRequest,
    ABVariantCreate,
    ABVariantResponse,
)
from app.utils.exceptions import BusinessError, NotFoundError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


def _to_response(exp: ABExperiment) -> ABExperimentResponse:
    return ABExperimentResponse(
        id=exp.id,
        key=exp.key,
        name=exp.name,
        description=exp.description or "",
        status=exp.status,
        alpha=float(exp.alpha or 0.05),
        min_sample_size=int(exp.min_sample_size or 100),
        primary_metric=exp.primary_metric or "conversion",
        control_variant_key=exp.control_variant_key,
        source_experiment_id=exp.source_experiment_id,
        config=exp.config or {},
        created_by=exp.created_by or "anonymous",
        started_at=exp.started_at,
        ended_at=exp.ended_at,
        winner_variant_key=exp.winner_variant_key,
        created_at=exp.created_at,
        variants=[
            ABVariantResponse(
                id=v.id,
                key=v.key,
                name=v.name or v.key,
                weight=float(v.weight or 1),
                is_control=bool(v.is_control),
                payload=v.payload or {},
                description=v.description or "",
            )
            for v in (exp.variants or [])
        ],
    )


@router.post("", response_model=ABExperimentResponse, status_code=201)
@require_permission(Permission.TASK_CREATE)
async def create_ab_experiment(
    body: ABExperimentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ABExperimentResponse:
    """Create an online A/B experiment with ≥2 variants."""
    actor = _actor(request)
    existing = (
        await session.execute(select(ABExperiment).where(ABExperiment.key == body.key))
    ).scalar_one_or_none()
    if existing:
        raise BusinessError(f"Experiment key already exists: {body.key}")

    controls = [v for v in body.variants if v.is_control]
    control_key = controls[0].key if controls else body.variants[0].key

    exp = ABExperiment(
        key=body.key,
        name=body.name,
        description=body.description or "",
        status=ABStatus.RUNNING.value if body.start_immediately else ABStatus.DRAFT.value,
        alpha=body.alpha,
        min_sample_size=body.min_sample_size,
        primary_metric=body.primary_metric,
        control_variant_key=control_key,
        source_experiment_id=body.source_experiment_id,
        config=body.config or {},
        created_by=actor,
        started_at=utcnow() if body.start_immediately else None,
    )
    session.add(exp)
    await session.flush()

    for i, v in enumerate(body.variants):
        is_ctrl = v.is_control or (not controls and i == 0)
        session.add(
            ABVariant(
                experiment_id=exp.id,
                key=v.key,
                name=v.name or v.key,
                weight=v.weight,
                is_control=is_ctrl,
                payload=v.payload or {},
                description=v.description or "",
            )
        )

    await write_audit(
        session,
        action="ab.create",
        resource_type="ab_experiment",
        resource_id=exp.id,
        actor=actor,
        detail={"key": body.key, "variants": [v.key for v in body.variants]},
    )
    await session.commit()
    exp = await ab_service.get_experiment_by_id(session, exp.id)
    return _to_response(exp)


@router.get("", response_model=ABExperimentListResponse)
@require_permission(Permission.TASK_READ)
async def list_ab_experiments(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> ABExperimentListResponse:
    actor = _actor(request)
    q = select(ABExperiment).options(selectinload(ABExperiment.variants))
    cq = select(func.count(ABExperiment.id))
    from app.core.tenancy import is_admin, tenancy_enforced

    if tenancy_enforced() and not is_admin(actor):
        q = q.where(ABExperiment.created_by == actor)
        cq = cq.where(ABExperiment.created_by == actor)
    if status:
        q = q.where(ABExperiment.status == status)
        cq = cq.where(ABExperiment.status == status)
    total = int((await session.execute(cq)).scalar() or 0)
    rows = (
        await session.execute(
            q.order_by(ABExperiment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ABExperimentListResponse(
        items=[_to_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/sample-size")
@require_permission(Permission.TASK_READ)
async def sample_size(
    body: ABSampleSizeRequest,
    request: Request,
) -> dict[str, Any]:
    """Recommend per-variant sample size for conversion-rate A/B tests."""
    return await ab_service.recommend_sample_size(
        baseline_rate=body.baseline_rate,
        mde=body.mde,
        alpha=body.alpha,
        power=body.power,
    )


@router.post(
    "/from-offline/{experiment_id}",
    response_model=ABExperimentResponse,
    status_code=201,
)
@require_permission(Permission.TASK_CREATE)
async def create_ab_from_offline_experiment(
    experiment_id: str,
    request: Request,
    key: str = Query(..., min_length=1, max_length=100),
    session: AsyncSession = Depends(get_db),
) -> ABExperimentResponse:
    """Promote an offline Experiment's runs into an online A/B draft."""
    from app.models.experiment import Experiment

    actor = _actor(request)
    offline = (
        await session.execute(
            select(Experiment)
            .options(selectinload(Experiment.runs))
            .where(Experiment.id == experiment_id)
        )
    ).scalar_one_or_none()
    if offline is None:
        raise NotFoundError("Experiment", experiment_id)
    if not offline.runs or len(offline.runs) < 2:
        raise BusinessError("Offline experiment needs at least 2 runs to create A/B")

    existing = (
        await session.execute(select(ABExperiment).where(ABExperiment.key == key))
    ).scalar_one_or_none()
    if existing:
        raise BusinessError(f"Experiment key already exists: {key}")

    variants = [
        ABVariantCreate(
            key=r.label,
            name=r.label,
            weight=1.0,
            is_control=(i == 0),
            payload={"agent_config": r.agent_config or {}},
        )
        for i, r in enumerate(offline.runs)
    ]
    exp = ABExperiment(
        key=key,
        name=f"AB from {offline.name}",
        description=f"Promoted from offline experiment {offline.id}",
        status=ABStatus.DRAFT.value,
        control_variant_key=variants[0].key,
        source_experiment_id=offline.id,
        created_by=actor,
        config={},
    )
    session.add(exp)
    await session.flush()
    for i, v in enumerate(variants):
        session.add(
            ABVariant(
                experiment_id=exp.id,
                key=v.key,
                name=v.name,
                weight=v.weight,
                is_control=v.is_control or i == 0,
                payload=v.payload,
            )
        )
    await session.commit()
    exp = await ab_service.get_experiment_by_id(session, exp.id)
    return _to_response(exp)


@router.get("/{experiment_id}", response_model=ABExperimentResponse)
@require_permission(Permission.TASK_READ)
async def get_ab_experiment(
    experiment_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ABExperimentResponse:
    exp = await ab_service.get_experiment_by_id(session, experiment_id)
    return _to_response(exp)


@router.patch("/{experiment_id}/status", response_model=ABExperimentResponse)
@require_permission(Permission.TASK_UPDATE)
async def update_ab_status(
    experiment_id: str,
    body: ABStatusUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ABExperimentResponse:
    exp = await ab_service.get_experiment_by_id(session, experiment_id)
    new_status = body.status
    if new_status == ABStatus.RUNNING.value and exp.status != ABStatus.RUNNING.value:
        exp.started_at = exp.started_at or utcnow()
        exp.ended_at = None
    if new_status in {ABStatus.COMPLETED.value, ABStatus.ARCHIVED.value}:
        exp.ended_at = utcnow()
    exp.status = new_status
    await session.commit()
    exp = await ab_service.get_experiment_by_id(session, experiment_id)
    return _to_response(exp)


@router.post("/{experiment_key}/assign", response_model=ABAssignResponse)
@require_permission(Permission.TASK_READ)
async def assign_unit(
    experiment_key: str,
    body: ABAssignRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ABAssignResponse:
    """Sticky assign a unit to a variant (and optionally log exposure)."""
    payload = await ab_service.assign(
        session,
        experiment_key=experiment_key,
        unit_id=body.unit_id,
        context=body.context,
        record_exposure=body.record_exposure,
    )
    return ABAssignResponse(**payload)


@router.post("/{experiment_key}/track")
@require_permission(Permission.TASK_UPDATE)
async def track_event(
    experiment_key: str,
    body: ABTrackRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Track exposure / conversion / metric for a unit."""
    return await ab_service.track_event(
        session,
        experiment_key=experiment_key,
        unit_id=body.unit_id,
        event_type=body.event_type,
        metric_name=body.metric_name,
        metric_value=body.metric_value,
        properties=body.properties,
        auto_assign=body.auto_assign,
    )


@router.get("/{experiment_id}/results")
@require_permission(Permission.EVALUATION_READ)
async def ab_results(
    experiment_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Statistical analysis: conversion rates, lift, p-values, optional winner."""
    return await ab_service.analyze(session, experiment_id)
