# (c) 2026 AgentFlow-Eval
"""Billing service — plans, quota, usage, invoices (feature-flagged)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.billing import (
    BillingPlan,
    Invoice,
    QuotaBalance,
    Subscription,
    UsageRecord,
)
from app.utils.exceptions import AgentFlowError

logger = logging.getLogger(__name__)


class QuotaExceededError(AgentFlowError):
    """HTTP 402 when billing is enabled and quota is exhausted."""

    def __init__(self, message: str = "Quota exceeded", detail: Any = None) -> None:
        super().__init__(message=message, status_code=402, detail=detail)


def period_key(dt: datetime | None = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.strftime("%Y-%m")


def billing_enabled() -> bool:
    return bool(getattr(settings, "BILLING_ENABLED", False))


def previous_period_key(dt: datetime | None = None) -> str:
    """Return YYYY-MM for the previous calendar month."""
    d = dt or datetime.now(timezone.utc)
    year, month = d.year, d.month
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


DEFAULT_PLANS: list[dict[str, Any]] = [
    {
        "code": "free",
        "name": "Free",
        "description": "Personal / demo tier",
        "price_month_cents": 0,
        "token_quota": 50_000,
        "task_quota": 50,
        "features": {
            "plugins": [
                "echo_tool",
                "audit_hooks",
                "length_judge",
                "echo_runner",
            ],
            "vision": False,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Small team private / SaaS starter",
        "price_month_cents": 4900,
        "token_quota": 1_000_000,
        "task_quota": 1000,
        "features": {
            "plugins": ["*"],
            "vision": True,
            "ab": True,
            "premium_plugins": True,
        },
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Unlimited private deployment baseline",
        "price_month_cents": 0,
        "token_quota": 100_000_000,
        "task_quota": 100_000,
        "features": {"plugins": ["*"], "vision": True, "ab": True, "sso": True},
    },
]


class BillingService:
    """Async helpers over billing tables."""

    async def ensure_default_plans(self, session: AsyncSession) -> int:
        created = 0
        for p in DEFAULT_PLANS:
            existing = await session.execute(
                select(BillingPlan).where(BillingPlan.code == p["code"])
            )
            if existing.scalar_one_or_none():
                continue
            session.add(
                BillingPlan(
                    id=str(uuid4()),
                    code=p["code"],
                    name=p["name"],
                    description=p["description"],
                    price_month_cents=p["price_month_cents"],
                    token_quota=p["token_quota"],
                    task_quota=p["task_quota"],
                    features=dict(p["features"]),
                    is_public=True,
                    is_active=True,
                )
            )
            created += 1
        if created:
            await session.flush()
        return created

    async def list_plans(
        self, session: AsyncSession, *, public_only: bool = True
    ) -> list[BillingPlan]:
        q = select(BillingPlan).where(BillingPlan.is_active.is_(True))
        if public_only:
            q = q.where(BillingPlan.is_public.is_(True))
        q = q.order_by(BillingPlan.price_month_cents.asc())
        rows = await session.execute(q)
        return list(rows.scalars().all())

    async def get_plan_by_code(
        self, session: AsyncSession, code: str
    ) -> BillingPlan | None:
        r = await session.execute(
            select(BillingPlan).where(BillingPlan.code == code)
        )
        return r.scalar_one_or_none()

    async def get_active_subscription(
        self, session: AsyncSession, actor: str
    ) -> Subscription | None:
        r = await session.execute(
            select(Subscription)
            .where(
                Subscription.actor == actor,
                Subscription.status.in_(("active", "trialing")),
            )
            .order_by(Subscription.created_at.desc())
        )
        return r.scalars().first()

    async def subscribe(
        self, session: AsyncSession, *, actor: str, plan_code: str
    ) -> Subscription:
        plan = await self.get_plan_by_code(session, plan_code)
        if plan is None:
            raise AgentFlowError(f"Unknown plan: {plan_code}", status_code=404)
        # Cancel previous active
        prev = await self.get_active_subscription(session, actor)
        if prev is not None:
            prev.status = "canceled"
        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=str(uuid4()),
            actor=actor,
            plan_id=plan.id,
            status="active",
            period_start=now,
        )
        session.add(sub)
        # Reset / init quota for period
        bal = await self._get_or_create_balance(session, actor, plan)
        bal.token_limit = plan.token_quota
        bal.task_limit = plan.task_quota
        await session.flush()
        return sub

    async def _resolve_limits(
        self, session: AsyncSession, actor: str
    ) -> tuple[int, int]:
        """Return (token_limit, task_limit) from sub plan or free defaults."""
        sub = await self.get_active_subscription(session, actor)
        if sub is not None:
            r = await session.execute(
                select(BillingPlan).where(BillingPlan.id == sub.plan_id)
            )
            plan = r.scalar_one_or_none()
            if plan:
                return plan.token_quota, plan.task_quota
        free = await self.get_plan_by_code(session, "free")
        if free:
            return free.token_quota, free.task_quota
        return 50_000, 50

    async def _get_or_create_balance(
        self,
        session: AsyncSession,
        actor: str,
        plan: BillingPlan | None = None,
    ) -> QuotaBalance:
        period = period_key()
        r = await session.execute(
            select(QuotaBalance).where(
                QuotaBalance.actor == actor, QuotaBalance.period == period
            )
        )
        bal = r.scalar_one_or_none()
        if bal:
            return bal
        token_limit, task_limit = (
            (plan.token_quota, plan.task_quota)
            if plan
            else await self._resolve_limits(session, actor)
        )
        bal = QuotaBalance(
            id=str(uuid4()),
            actor=actor,
            period=period,
            token_used=0,
            token_limit=token_limit,
            task_used=0,
            task_limit=task_limit,
        )
        session.add(bal)
        await session.flush()
        return bal

    async def get_quota(self, session: AsyncSession, actor: str) -> dict[str, Any]:
        await self.ensure_default_plans(session)
        bal = await self._get_or_create_balance(session, actor)
        sub = await self.get_active_subscription(session, actor)
        plan_code = None
        if sub:
            plan = (
                await session.execute(
                    select(BillingPlan).where(BillingPlan.id == sub.plan_id)
                )
            ).scalar_one_or_none()
            plan_code = plan.code if plan else None
        return {
            "actor": actor,
            "period": bal.period,
            "token_used": bal.token_used,
            "token_limit": bal.token_limit,
            "task_used": bal.task_used,
            "task_limit": bal.task_limit,
            "plan_code": plan_code or "free",
            "subscription_status": sub.status if sub else "none",
            "billing_enabled": billing_enabled(),
        }

    async def ensure_task_quota(self, session: AsyncSession, actor: str) -> None:
        """Raise QuotaExceededError if task quota exhausted (when billing on)."""
        if not billing_enabled():
            return
        await self.ensure_default_plans(session)
        bal = await self._get_or_create_balance(session, actor)
        if bal.task_used >= bal.task_limit:
            raise QuotaExceededError(
                "Task quota exceeded for this billing period",
                detail={
                    "task_used": bal.task_used,
                    "task_limit": bal.task_limit,
                    "period": bal.period,
                },
            )

    async def record_usage(
        self,
        session: AsyncSession,
        *,
        actor: str,
        metric: str,
        quantity: float = 1.0,
        ref_type: str | None = None,
        ref_id: str | None = None,
        trace_id: str | None = None,
        extra: dict[str, Any] | None = None,
        consume_quota: bool = True,
    ) -> UsageRecord:
        rec = UsageRecord(
            id=str(uuid4()),
            actor=actor or "anonymous",
            metric=metric,
            quantity=float(quantity),
            unit_cost=0.0,
            ref_type=ref_type,
            ref_id=ref_id,
            trace_id=trace_id,
            extra=dict(extra or {}),
        )
        session.add(rec)
        if consume_quota and billing_enabled():
            bal = await self._get_or_create_balance(session, actor or "anonymous")
            if metric == "task":
                bal.task_used = int(bal.task_used) + int(quantity)
            elif metric in {"token", "tokens"}:
                bal.token_used = float(bal.token_used) + float(quantity)
            elif metric == "judge":
                # judge counts toward token-ish soft budget: +100 abstract units
                bal.token_used = float(bal.token_used) + float(quantity) * 100
        await session.flush()
        return rec

    async def list_usage(
        self,
        session: AsyncSession,
        actor: str,
        *,
        limit: int = 100,
    ) -> list[UsageRecord]:
        r = await session.execute(
            select(UsageRecord)
            .where(UsageRecord.actor == actor)
            .order_by(UsageRecord.created_at.desc())
            .limit(min(limit, 500))
        )
        return list(r.scalars().all())

    async def list_invoices(
        self, session: AsyncSession, actor: str
    ) -> list[Invoice]:
        r = await session.execute(
            select(Invoice)
            .where(Invoice.actor == actor)
            .order_by(Invoice.created_at.desc())
        )
        return list(r.scalars().all())

    async def draft_invoice(
        self, session: AsyncSession, actor: str, *, period: str | None = None
    ) -> Invoice:
        """Aggregate usage for period into a draft invoice."""
        p = period or period_key()
        # Simple: plan price only + usage summary line
        sub = await self.get_active_subscription(session, actor)
        amount = 0
        lines: list[dict[str, Any]] = []
        if sub:
            plan = (
                await session.execute(
                    select(BillingPlan).where(BillingPlan.id == sub.plan_id)
                )
            ).scalar_one_or_none()
            if plan:
                amount = plan.price_month_cents
                lines.append(
                    {
                        "type": "plan",
                        "code": plan.code,
                        "amount_cents": plan.price_month_cents,
                    }
                )
        bal = await self._get_or_create_balance(session, actor)
        lines.append(
            {
                "type": "usage_summary",
                "token_used": bal.token_used,
                "task_used": bal.task_used,
                "period": p,
            }
        )
        inv = Invoice(
            id=str(uuid4()),
            actor=actor,
            period=p,
            amount_cents=amount,
            status="draft",
            line_items=lines,
            issued_at=datetime.now(timezone.utc),
        )
        session.add(inv)
        await session.flush()
        return inv

    def plan_allows_plugin(self, features: dict[str, Any] | None, plugin_id: str) -> bool:
        if not features:
            return True
        plugins = features.get("plugins")
        if plugins is None:
            return True
        if plugins == ["*"] or plugins == "*":
            return True
        return plugin_id in set(plugins or [])

    async def rollover_period(
        self,
        session: AsyncSession,
        actor: str,
        *,
        new_period: str | None = None,
    ) -> QuotaBalance:
        """Create a fresh quota balance for a new period (monthly reset).

        Does not delete historical balances; new period starts counters at 0
        with limits from the active plan (or free defaults).
        """
        period = new_period or period_key()
        existing = await session.execute(
            select(QuotaBalance).where(
                QuotaBalance.actor == actor, QuotaBalance.period == period
            )
        )
        bal = existing.scalar_one_or_none()
        if bal is not None:
            return bal
        token_limit, task_limit = await self._resolve_limits(session, actor)
        bal = QuotaBalance(
            id=str(uuid4()),
            actor=actor,
            period=period,
            token_used=0,
            token_limit=token_limit,
            task_used=0,
            task_limit=task_limit,
        )
        session.add(bal)
        await session.flush()
        logger.info(
            "Quota rollover actor=%s period=%s limits token=%s task=%s",
            actor,
            period,
            token_limit,
            task_limit,
        )
        return bal

    async def rollover_all_active(
        self, session: AsyncSession, *, period: str | None = None
    ) -> int:
        """Ensure current-period balances exist for all actors with subscriptions."""
        period = period or period_key()
        rows = await session.execute(
            select(Subscription.actor)
            .where(Subscription.status.in_(("active", "trialing")))
            .distinct()
        )
        actors = [r[0] for r in rows.all()]
        count = 0
        for actor in actors:
            await self.rollover_period(session, actor, new_period=period)
            count += 1
        return count


_svc: BillingService | None = None


def get_billing_service() -> BillingService:
    global _svc
    if _svc is None:
        _svc = BillingService()
    return _svc
