# (c) 2026 AgentFlow-Eval
"""Stripe Checkout placeholder — mock sessions + optional live Stripe SDK."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)


def stripe_mode() -> str:
    mode = (getattr(settings, "STRIPE_MODE", None) or "mock").lower().strip()
    if (
        mode == "live"
        and not (getattr(settings, "STRIPE_SECRET_KEY", "") or "").strip()
    ):
        logger.warning(
            "STRIPE_MODE=live but STRIPE_SECRET_KEY empty — falling back to mock"
        )
        return "mock"
    return mode if mode in {"mock", "live"} else "mock"


def parse_price_ids(raw: str | None = None) -> dict[str, str]:
    text = raw if raw is not None else getattr(settings, "STRIPE_PRICE_IDS", "") or ""
    out: dict[str, str] = {}
    for part in str(text).split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        code, price = part.split(":", 1)
        out[code.strip().lower()] = price.strip()
    return out


def create_checkout_session(
    *,
    actor: str,
    plan_code: str,
    plan_name: str,
    amount_cents: int,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict[str, Any]:
    """Create a Checkout Session (mock URL or live Stripe).

    Returns dict with session_id, url, mode, plan_code, actor.
    """
    plan_code = (plan_code or "").lower().strip()
    if plan_code in {"", "free"}:
        raise ValueError("free plan does not require checkout")

    success = success_url or settings.STRIPE_SUCCESS_URL
    cancel = cancel_url or settings.STRIPE_CANCEL_URL
    mode = stripe_mode()

    if mode == "live":
        return _create_live_session(
            actor=actor,
            plan_code=plan_code,
            plan_name=plan_name,
            amount_cents=amount_cents,
            success_url=success,
            cancel_url=cancel,
        )
    return _create_mock_session(
        actor=actor,
        plan_code=plan_code,
        plan_name=plan_name,
        amount_cents=amount_cents,
        success_url=success,
        cancel_url=cancel,
    )


def _create_mock_session(
    *,
    actor: str,
    plan_code: str,
    plan_name: str,
    amount_cents: int,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    sid = f"cs_test_mock_{uuid4().hex[:24]}"
    # Mock "hosted" page is our own confirm endpoint hint
    # Frontend can open success URL with session_id after mock confirm
    base = success_url.split("?")[0]
    mock_pay_url = (
        f"{base}?checkout=mock_pending&session_id={sid}"
        f"&plan_code={plan_code}&actor={actor}"
    )
    return {
        "session_id": sid,
        "url": mock_pay_url,
        "mode": "mock",
        "plan_code": plan_code,
        "plan_name": plan_name,
        "amount_cents": amount_cents,
        "actor": actor,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "message": "Mock Checkout — call POST /billing/checkout/mock-confirm to complete",
    }


def _create_live_session(
    *,
    actor: str,
    plan_code: str,
    plan_name: str,
    amount_cents: int,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    try:
        import stripe  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "stripe package not installed; pip install stripe or use STRIPE_MODE=mock"
        ) from exc

    stripe.api_key = settings.STRIPE_SECRET_KEY
    price_ids = parse_price_ids()
    price_id = price_ids.get(plan_code)

    metadata = {
        "actor": actor,
        "plan_code": plan_code,
        "app": "agentflow-eval",
    }

    success = (
        success_url
        + ("&" if "?" in success_url else "?")
        + "session_id={CHECKOUT_SESSION_ID}"
    )

    if price_id:
        session = stripe.checkout.Session.create(
            mode="subscription",
            success_url=success,
            cancel_url=cancel_url,
            line_items=[{"price": price_id, "quantity": 1}],
            client_reference_id=actor,
            metadata=metadata,
        )
    else:
        # One-time payment fallback when no Price ID mapped
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success,
            cancel_url=cancel_url,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"AgentFlow {plan_name}"},
                        "unit_amount": max(0, int(amount_cents)),
                    },
                    "quantity": 1,
                }
            ],
            client_reference_id=actor,
            metadata=metadata,
        )

    return {
        "session_id": session.id,
        "url": session.url,
        "mode": "live",
        "plan_code": plan_code,
        "plan_name": plan_name,
        "amount_cents": amount_cents,
        "actor": actor,
    }


def verify_webhook_signature(
    payload: bytes,
    sig_header: str | None,
    *,
    secret: str | None = None,
) -> bool:
    """Verify Stripe-Signature (live) or accept mock when secret empty / mock mode."""
    mode = stripe_mode()
    secret = (secret if secret is not None else settings.STRIPE_WEBHOOK_SECRET) or ""
    if mode == "mock" or not secret:
        return True
    if not sig_header:
        return False
    try:
        import stripe  # type: ignore

        stripe.Webhook.construct_event(payload, sig_header, secret)
        return True
    except Exception:
        # Minimal HMAC fallback if stripe SDK missing
        try:
            # Stripe uses t=timestamp,v1=signature
            parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
            timestamp = parts.get("t", "")
            v1 = parts.get("v1", "")
            signed = f"{timestamp}.".encode() + payload
            digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
            return hmac.compare_digest(digest, v1)
        except Exception as exc:
            logger.warning("webhook signature verify failed: %s", exc)
            return False


def parse_checkout_completed_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Extract actor + plan_code from checkout.session.completed style payload."""
    etype = event.get("type") or event.get("event_type") or ""
    if etype and etype not in {
        "checkout.session.completed",
        "mock.checkout.completed",
    }:
        return None
    data = event.get("data") or {}
    obj = data.get("object") if isinstance(data, dict) else None
    if obj is None and isinstance(event.get("session"), dict):
        obj = event["session"]
    if not isinstance(obj, dict):
        obj = event if event.get("plan_code") or event.get("metadata") else None
    if not isinstance(obj, dict):
        return None

    meta = obj.get("metadata") or {}
    actor = (
        meta.get("actor")
        or obj.get("client_reference_id")
        or obj.get("actor")
        or "anonymous"
    )
    plan_code = (meta.get("plan_code") or obj.get("plan_code") or "").lower().strip()
    session_id = obj.get("id") or obj.get("session_id") or ""
    if not plan_code:
        return None
    return {
        "actor": str(actor),
        "plan_code": plan_code,
        "session_id": str(session_id),
        "external_ref": str(session_id),
    }


def build_mock_completed_event(
    *,
    actor: str,
    plan_code: str,
    session_id: str,
) -> dict[str, Any]:
    return {
        "id": f"evt_mock_{uuid4().hex[:16]}",
        "type": "mock.checkout.completed",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "client_reference_id": actor,
                "metadata": {"actor": actor, "plan_code": plan_code},
                "payment_status": "paid",
                "status": "complete",
            }
        },
    }
