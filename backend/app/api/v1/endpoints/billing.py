# (c) 2026 AgentFlow-Eval
"""Billing / subscription / usage APIs (BILLING_ENABLED optional)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request  # Query used by rollover
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.billing.service import billing_enabled, get_billing_service
from app.core.dependencies import get_db
from app.core.rbac import Permission, require_permission
from app.utils.exceptions import AgentFlowError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


class SubscribeBody(BaseModel):
    plan_code: str = Field(..., description="free | pro | enterprise")


def _plan_dict(p) -> dict[str, Any]:
    return {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "description": p.description,
        "price_month_cents": p.price_month_cents,
        "billing_cycle": getattr(p, "billing_cycle", None) or "monthly",
        "token_quota": p.token_quota,
        "task_quota": p.task_quota,
        "storage_quota_mb": getattr(p, "storage_quota_mb", None),
        "plugin_quota": getattr(p, "plugin_quota", None),
        "features": p.features or {},
        "limits": (p.features or {}).get("limits")
        or {
            "tasks": p.task_quota,
            "tokens": p.token_quota,
            "storage_mb": getattr(p, "storage_quota_mb", None),
            "plugins": getattr(p, "plugin_quota", None),
        },
        "is_public": p.is_public,
    }


@router.get("/plans")
@require_permission(Permission.BILLING_READ, Permission.TASK_READ, require_all=False)
async def list_plans(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    plans = await svc.list_plans(session, public_only=True)
    return {
        "items": [_plan_dict(p) for p in plans],
        "total": len(plans),
        "billing_enabled": billing_enabled(),
    }


@router.get("/plan")
@require_permission(Permission.BILLING_READ, Permission.TASK_READ, require_all=False)
async def get_current_plan(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Current actor plan + quota (enterprise contract alias)."""
    actor = _actor(request)
    svc = get_billing_service()
    return await svc.get_current_plan(session, actor)


@router.get("/quota")
@require_permission(Permission.BILLING_READ, Permission.TASK_READ, require_all=False)
async def get_quota(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    actor = _actor(request)
    svc = get_billing_service()
    return await svc.get_quota(session, actor)


@router.get("/usage")
@require_permission(Permission.BILLING_READ, Permission.TASK_READ, require_all=False)
async def list_usage(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    actor = _actor(request)
    svc = get_billing_service()
    rows = await svc.list_usage(session, actor, limit=limit)
    return {
        "items": [
            {
                "id": r.id,
                "metric": r.metric,
                "quantity": r.quantity,
                "ref_type": r.ref_type,
                "ref_id": r.ref_id,
                "trace_id": r.trace_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
        "billing_enabled": billing_enabled(),
    }


class CheckoutBody(BaseModel):
    plan_code: str = Field(..., description="pro | enterprise (not free)")
    success_url: str | None = None
    cancel_url: str | None = None


class MockConfirmBody(BaseModel):
    session_id: str
    plan_code: str
    actor: str | None = None


@router.post("/subscribe")
@require_permission(
    Permission.BILLING_MANAGE, Permission.SYSTEM_CONFIG, require_all=False
)
async def subscribe(
    request: Request,
    body: SubscribeBody,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Direct subscribe (ops / free tier / mock without payment).

    Paid plans in production should use ``POST /billing/checkout``.
    """
    actor = _actor(request)
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    try:
        sub = await svc.subscribe(session, actor=actor, plan_code=body.plan_code)
    except AgentFlowError:
        raise
    except Exception as exc:
        raise AgentFlowError(f"subscribe failed: {exc}", status_code=400) from exc
    await session.commit()
    return {
        "subscription": {
            "id": sub.id,
            "actor": sub.actor,
            "plan_id": sub.plan_id,
            "status": sub.status,
        }
    }


@router.post("/checkout")
@require_permission(
    Permission.BILLING_MANAGE, Permission.SYSTEM_CONFIG, require_all=False
)
async def create_checkout(
    request: Request,
    body: CheckoutBody,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create Stripe Checkout session (mock by default).

    Returns ``url`` to redirect the browser. In mock mode, complete with
    ``POST /billing/checkout/mock-confirm``.
    """
    from app.core.billing.stripe_checkout import create_checkout_session, stripe_mode

    actor = _actor(request)
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    plan = await svc.get_plan_by_code(session, body.plan_code)
    if plan is None:
        raise AgentFlowError(f"Unknown plan: {body.plan_code}", status_code=404)
    if plan.code == "free" or plan.price_month_cents <= 0:
        # Free: subscribe immediately
        sub = await svc.subscribe(session, actor=actor, plan_code="free")
        await session.commit()
        return {
            "mode": "direct",
            "url": None,
            "subscription": {
                "id": sub.id,
                "actor": sub.actor,
                "plan_id": sub.plan_id,
                "status": sub.status,
            },
        }
    try:
        session_out = create_checkout_session(
            actor=actor,
            plan_code=plan.code,
            plan_name=plan.name,
            amount_cents=plan.price_month_cents,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except Exception as exc:
        raise AgentFlowError(f"checkout failed: {exc}", status_code=400) from exc
    return {
        "checkout": session_out,
        "stripe_mode": stripe_mode(),
        "billing_enabled": billing_enabled(),
    }


@router.post("/checkout/mock-confirm")
@require_permission(
    Permission.BILLING_MANAGE, Permission.SYSTEM_CONFIG, require_all=False
)
async def mock_confirm_checkout(
    request: Request,
    body: MockConfirmBody,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Complete a mock Checkout session and activate the subscription."""
    from app.core.billing.stripe_checkout import (
        build_mock_completed_event,
        parse_checkout_completed_event,
        stripe_mode,
    )

    if stripe_mode() != "mock":
        raise AgentFlowError(
            "mock-confirm only available when STRIPE_MODE=mock",
            status_code=400,
        )
    actor = body.actor or _actor(request)
    event = build_mock_completed_event(
        actor=actor,
        plan_code=body.plan_code,
        session_id=body.session_id,
    )
    parsed = parse_checkout_completed_event(event)
    if not parsed:
        raise AgentFlowError("invalid mock session", status_code=400)
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    try:
        sub = await svc.subscribe(
            session, actor=parsed["actor"], plan_code=parsed["plan_code"]
        )
        sub.external_ref = parsed.get("external_ref") or body.session_id
    except Exception as exc:
        raise AgentFlowError(f"activate failed: {exc}", status_code=400) from exc
    await session.commit()
    return {
        "ok": True,
        "mode": "mock",
        "subscription": {
            "id": sub.id,
            "actor": sub.actor,
            "plan_id": sub.plan_id,
            "status": sub.status,
            "external_ref": sub.external_ref,
        },
    }


async def _handle_stripe_webhook(
    request: Request,
    session: AsyncSession,
) -> dict[str, Any]:
    """Shared Stripe/mock webhook body (public — signature verified)."""
    from app.core.billing.stripe_checkout import (
        parse_checkout_completed_event,
        verify_webhook_signature,
    )

    payload = await request.body()
    sig = request.headers.get("stripe-signature") or request.headers.get(
        "Stripe-Signature"
    )
    if not verify_webhook_signature(payload, sig):
        raise AgentFlowError("invalid webhook signature", status_code=400)

    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except Exception as exc:
        raise AgentFlowError(f"invalid JSON: {exc}", status_code=400) from exc

    parsed = parse_checkout_completed_event(event)
    if not parsed:
        return {"received": True, "handled": False, "reason": "ignored_event"}

    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    try:
        sub = await svc.subscribe(
            session,
            actor=parsed["actor"],
            plan_code=parsed["plan_code"],
        )
        if parsed.get("external_ref"):
            sub.external_ref = parsed["external_ref"]
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise AgentFlowError(
            f"webhook activate failed: {exc}", status_code=400
        ) from exc

    try:
        from app.core.audit import write_audit

        await write_audit(
            session,
            action="billing.checkout_completed",
            resource_type="subscription",
            resource_id=sub.id,
            actor=parsed["actor"],
            detail={
                "plan_code": parsed["plan_code"],
                "session_id": parsed.get("session_id"),
                "source": "stripe_webhook",
            },
        )
        await session.commit()
    except Exception:
        pass

    return {
        "received": True,
        "handled": True,
        "actor": parsed["actor"],
        "plan_code": parsed["plan_code"],
        "subscription_id": sub.id,
    }


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Stripe webhook receiver (public path — signature verified)."""
    return await _handle_stripe_webhook(request, session)


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Stripe-compatible webhook alias (POST /api/v1/billing/webhook)."""
    return await _handle_stripe_webhook(request, session)


@router.get("/invoices")
@require_permission(Permission.TASK_READ)
async def list_invoices(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    actor = _actor(request)
    svc = get_billing_service()
    invs = await svc.list_invoices(session, actor)
    return {
        "items": [
            {
                "id": i.id,
                "period": i.period,
                "amount_cents": i.amount_cents,
                "status": i.status,
                "line_items": i.line_items,
                "issued_at": i.issued_at.isoformat() if i.issued_at else None,
            }
            for i in invs
        ],
        "total": len(invs),
    }


@router.post("/invoices/draft")
@require_permission(Permission.SYSTEM_CONFIG)
async def create_draft_invoice(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    actor = _actor(request)
    svc = get_billing_service()
    inv = await svc.draft_invoice(session, actor)
    await session.commit()
    return {
        "invoice": {
            "id": inv.id,
            "period": inv.period,
            "amount_cents": inv.amount_cents,
            "status": inv.status,
            "line_items": inv.line_items,
        }
    }


@router.post("/quota/rollover")
@require_permission(Permission.SYSTEM_CONFIG)
async def rollover_quota(
    request: Request,
    session: AsyncSession = Depends(get_db),
    all_actors: bool = Query(False, description="Reset all subscribed actors"),
) -> dict[str, Any]:
    """Create a fresh quota balance for the current calendar month.

    Idempotent for the current period. Used by ops cron or manual admin.
    """
    svc = get_billing_service()
    await svc.ensure_default_plans(session)
    if all_actors:
        n = await svc.rollover_all_active(session)
        await session.commit()
        return {"rolled": n, "scope": "all_active"}
    actor = _actor(request)
    bal = await svc.rollover_period(session, actor)
    await session.commit()
    return {
        "rolled": 1,
        "scope": "self",
        "quota": {
            "actor": bal.actor,
            "period": bal.period,
            "task_used": bal.task_used,
            "task_limit": bal.task_limit,
            "token_used": bal.token_used,
            "token_limit": bal.token_limit,
        },
    }
