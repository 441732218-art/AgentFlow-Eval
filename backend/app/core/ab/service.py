# (c) 2026 AgentFlow-Eval
"""A/B experiment domain service: assign, track, analyze."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ab.assignment import VariantWeight, assign_variant, stable_bucket
from app.core.ab.stats import (
    sample_size_proportion,
    two_proportion_z_test,
    welch_t_test,
)
from app.models.ab_test import (
    ABAssignment,
    ABEvent,
    ABExperiment,
    ABStatus,
    ABVariant,
)
from app.utils.exceptions import BusinessError, NotFoundError


async def get_experiment_by_key(
    session: AsyncSession,
    key: str,
    *,
    with_variants: bool = True,
) -> ABExperiment:
    q = select(ABExperiment).where(ABExperiment.key == key)
    if with_variants:
        q = q.options(selectinload(ABExperiment.variants))
    exp = (await session.execute(q)).scalar_one_or_none()
    if exp is None:
        raise NotFoundError("ABExperiment", key)
    return exp


async def get_experiment_by_id(
    session: AsyncSession,
    experiment_id: str,
    *,
    with_variants: bool = True,
) -> ABExperiment:
    q = select(ABExperiment).where(ABExperiment.id == experiment_id)
    if with_variants:
        q = q.options(selectinload(ABExperiment.variants))
    exp = (await session.execute(q)).scalar_one_or_none()
    if exp is None:
        raise NotFoundError("ABExperiment", experiment_id)
    return exp


async def assign(
    session: AsyncSession,
    *,
    experiment_key: str,
    unit_id: str,
    context: dict[str, Any] | None = None,
    record_exposure: bool = True,
) -> dict[str, Any]:
    """Return sticky assignment; create row if new; optionally log exposure."""
    exp = await get_experiment_by_key(session, experiment_key)
    existing = await _get_assignment(session, exp.id, unit_id)
    if existing:
        # Sticky: always return prior assignment (even if paused/completed)
        variant = _variant_by_key(exp, existing.variant_key)
        if record_exposure and exp.status == ABStatus.RUNNING.value:
            await _add_event(
                session,
                experiment_id=exp.id,
                unit_id=unit_id,
                variant_key=existing.variant_key,
                event_type="exposure",
            )
            await session.commit()
        return _assignment_payload(exp, existing, variant, is_new=False)

    # New units only when experiment is running
    if exp.status != ABStatus.RUNNING.value:
        raise BusinessError(
            f"Experiment is {exp.status}; only running experiments accept new units"
        )

    weights = [
        VariantWeight(key=v.key, weight=float(v.weight or 0))
        for v in exp.variants
    ]
    chosen = assign_variant(exp.key, unit_id, weights)
    bucket = stable_bucket(exp.key, unit_id)
    row = ABAssignment(
        experiment_id=exp.id,
        unit_id=unit_id,
        variant_key=chosen,
        bucket=bucket,
        context=context,
    )
    session.add(row)
    if record_exposure:
        session.add(
            ABEvent(
                experiment_id=exp.id,
                unit_id=unit_id,
                variant_key=chosen,
                event_type="exposure",
            )
        )
    await session.commit()
    await session.refresh(row)
    variant = _variant_by_key(exp, chosen)
    return _assignment_payload(exp, row, variant, is_new=True)


async def track_event(
    session: AsyncSession,
    *,
    experiment_key: str,
    unit_id: str,
    event_type: str,
    metric_name: str | None = None,
    metric_value: float | None = None,
    properties: dict[str, Any] | None = None,
    auto_assign: bool = True,
) -> dict[str, Any]:
    """Record conversion/metric/exposure; optionally assign first."""
    exp = await get_experiment_by_key(session, experiment_key)
    assignment = await _get_assignment(session, exp.id, unit_id)
    if assignment is None:
        if not auto_assign:
            raise BusinessError("Unit not assigned; call /assign first")
        payload = await assign(
            session,
            experiment_key=experiment_key,
            unit_id=unit_id,
            record_exposure=event_type != "exposure",
        )
        variant_key = payload["variant_key"]
    else:
        variant_key = assignment.variant_key

    et = (event_type or "metric").strip().lower()
    if et not in {"exposure", "conversion", "metric"}:
        raise BusinessError("event_type must be exposure|conversion|metric")

    event = ABEvent(
        experiment_id=exp.id,
        unit_id=unit_id,
        variant_key=variant_key,
        event_type=et,
        metric_name=metric_name or (exp.primary_metric if et == "metric" else None),
        metric_value=metric_value if et != "exposure" else None,
        properties=properties,
    )
    # conversion defaults metric_value to 1
    if et == "conversion" and event.metric_value is None:
        event.metric_value = 1.0
        event.metric_name = event.metric_name or "conversion"

    session.add(event)
    await session.commit()
    await session.refresh(event)
    return {
        "event_id": event.id,
        "experiment_key": exp.key,
        "unit_id": unit_id,
        "variant_key": variant_key,
        "event_type": et,
        "metric_name": event.metric_name,
        "metric_value": event.metric_value,
    }


async def analyze(
    session: AsyncSession,
    experiment_id: str,
) -> dict[str, Any]:
    """Compute traffic, conversion rates, and significance vs control."""
    exp = await get_experiment_by_id(session, experiment_id)
    control_key = exp.control_variant_key or _default_control_key(exp)

    # Exposures per variant (unique units)
    exp_rows = (
        await session.execute(
            select(ABEvent.variant_key, ABEvent.unit_id)
            .where(
                ABEvent.experiment_id == exp.id,
                ABEvent.event_type == "exposure",
            )
            .distinct()
        )
    ).all()
    exposures: dict[str, set[str]] = defaultdict(set)
    for vk, uid in exp_rows:
        exposures[str(vk)].add(str(uid))

    # Conversions: unique units with conversion event
    conv_rows = (
        await session.execute(
            select(ABEvent.variant_key, ABEvent.unit_id)
            .where(
                ABEvent.experiment_id == exp.id,
                ABEvent.event_type == "conversion",
            )
            .distinct()
        )
    ).all()
    conversions: dict[str, set[str]] = defaultdict(set)
    for vk, uid in conv_rows:
        conversions[str(vk)].add(str(uid))

    # Continuous metrics
    metric_name = exp.primary_metric if exp.primary_metric != "conversion" else None
    metric_values: dict[str, list[float]] = defaultdict(list)
    if metric_name and metric_name != "conversion":
        m_rows = (
            await session.execute(
                select(ABEvent.variant_key, ABEvent.metric_value).where(
                    ABEvent.experiment_id == exp.id,
                    ABEvent.event_type == "metric",
                    ABEvent.metric_name == metric_name,
                    ABEvent.metric_value.is_not(None),
                )
            )
        ).all()
        for vk, val in m_rows:
            metric_values[str(vk)].append(float(val))

    control_n = len(exposures.get(control_key or "", set()))
    control_c = len(conversions.get(control_key or "", set()))
    control_metrics = metric_values.get(control_key or "", [])

    variants_out: list[dict[str, Any]] = []
    for v in exp.variants:
        n = len(exposures.get(v.key, set()))
        c = len(conversions.get(v.key, set()))
        rate = c / n if n else 0.0
        item: dict[str, Any] = {
            "variant_key": v.key,
            "name": v.name or v.key,
            "is_control": v.key == control_key or bool(v.is_control),
            "weight": v.weight,
            "exposures": n,
            "conversions": c,
            "conversion_rate": round(rate, 6),
            "payload": v.payload or {},
        }
        vals = metric_values.get(v.key, [])
        if vals:
            item["metric_name"] = metric_name
            item["metric_n"] = len(vals)
            item["metric_mean"] = round(sum(vals) / len(vals), 4)

        if v.key != control_key and control_key:
            # Proportion test on conversion
            prop = two_proportion_z_test(
                control_c, control_n, c, n, alpha=float(exp.alpha or 0.05)
            )
            item["conversion_test"] = prop.to_dict()
            if control_metrics and vals:
                mean_t = welch_t_test(
                    control_metrics, vals, alpha=float(exp.alpha or 0.05)
                )
                item["metric_test"] = mean_t.to_dict()
        variants_out.append(item)

    # Guardrails
    min_n = int(exp.min_sample_size or 0)
    enough = all(
        (len(exposures.get(v.key, set())) >= min_n) for v in exp.variants
    ) if exp.variants else False

    # Suggest winner: significant treatment with highest conversion (or metric)
    winner = None
    if enough and control_key:
        candidates = []
        for item in variants_out:
            if item["variant_key"] == control_key:
                continue
            test = item.get("conversion_test") or {}
            if test.get("significant") and test.get("absolute_lift", 0) > 0:
                candidates.append(item)
        if candidates:
            winner = max(candidates, key=lambda x: x.get("conversion_rate", 0))[
                "variant_key"
            ]

    return {
        "experiment_id": exp.id,
        "key": exp.key,
        "name": exp.name,
        "status": exp.status,
        "primary_metric": exp.primary_metric,
        "alpha": exp.alpha,
        "min_sample_size": min_n,
        "control_variant_key": control_key,
        "sample_size_ok": enough,
        "winner_variant_key": winner or exp.winner_variant_key,
        "variants": variants_out,
    }


async def recommend_sample_size(
    *,
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> dict[str, Any]:
    n = sample_size_proportion(baseline_rate, mde, alpha=alpha, power=power)
    return {
        "per_variant": n,
        "total_for_two_arms": n * 2,
        "baseline_rate": baseline_rate,
        "mde": mde,
        "alpha": alpha,
        "power": power,
    }


# ---- helpers ----


async def _get_assignment(
    session: AsyncSession, experiment_id: str, unit_id: str
) -> ABAssignment | None:
    return (
        await session.execute(
            select(ABAssignment).where(
                ABAssignment.experiment_id == experiment_id,
                ABAssignment.unit_id == unit_id,
            )
        )
    ).scalar_one_or_none()


def _variant_by_key(exp: ABExperiment, key: str) -> ABVariant | None:
    for v in exp.variants or []:
        if v.key == key:
            return v
    return None


def _default_control_key(exp: ABExperiment) -> str | None:
    for v in exp.variants or []:
        if v.is_control:
            return v.key
    return exp.variants[0].key if exp.variants else None


def _assignment_payload(
    exp: ABExperiment,
    row: ABAssignment,
    variant: ABVariant | None,
    *,
    is_new: bool,
) -> dict[str, Any]:
    return {
        "experiment_id": exp.id,
        "experiment_key": exp.key,
        "unit_id": row.unit_id,
        "variant_key": row.variant_key,
        "bucket": row.bucket,
        "is_new": is_new,
        "is_control": bool(variant.is_control) if variant else False,
        "payload": (variant.payload if variant else {}) or {},
        "status": exp.status,
    }


async def _add_event(
    session: AsyncSession,
    *,
    experiment_id: str,
    unit_id: str,
    variant_key: str,
    event_type: str,
) -> None:
    session.add(
        ABEvent(
            experiment_id=experiment_id,
            unit_id=unit_id,
            variant_key=variant_key,
            event_type=event_type,
        )
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
