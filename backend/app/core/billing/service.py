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
    """HTTP 429 QUOTA_EXCEEDED when billing is enabled and quota is exhausted.

    Legacy clients that only handled 402 should also treat 429 as quota failure.
    """

    def __init__(
        self,
        message: str = "Quota exceeded",
        detail: Any = None,
        *,
        metric: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"code": "QUOTA_EXCEEDED"}
        if isinstance(detail, dict):
            payload.update(detail)
        elif detail is not None:
            payload["detail"] = detail
        if metric:
            payload["metric"] = metric
        super().__init__(message=message, status_code=429, detail=payload)


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
        "billing_cycle": "monthly",
        "token_quota": 50_000,
        "task_quota": 50,
        "storage_quota_mb": 500,
        "plugin_quota": 4,
        "features": {
            "plugins": [
                "echo_tool",
                "audit_hooks",
                "length_judge",
                "echo_runner",
            ],
            "vision": False,
            "limits": {
                "tasks": 50,
                "tokens": 50_000,
                "storage_mb": 500,
                "plugins": 4,
            },
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Small team private / SaaS starter",
        "price_month_cents": 4900,
        "billing_cycle": "monthly",
        "token_quota": 1_000_000,
        "task_quota": 1000,
        "storage_quota_mb": 10_000,
        "plugin_quota": 50,
        "features": {
            "plugins": ["*"],
            "vision": True,
            "ab": True,
            "premium_plugins": True,
            "benchmark": True,
            "limits": {
                "tasks": 1000,
                "tokens": 1_000_000,
                "storage_mb": 10_000,
                "plugins": 50,
            },
        },
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Unlimited private deployment baseline",
        "price_month_cents": 0,
        "billing_cycle": "monthly",
        "token_quota": 100_000_000,
        "task_quota": 100_000,
        "storage_quota_mb": 1_000_000,
        "plugin_quota": 10_000,
        "features": {
            "plugins": ["*"],
            "vision": True,
            "ab": True,
            "sso": True,
            "benchmark": True,
            "limits": {
                "tasks": 100_000,
                "tokens": 100_000_000,
                "storage_mb": 1_000_000,
                "plugins": 10_000,
            },
        },
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
                    **{
                        k: p[k]
                        for k in (
                            "billing_cycle",
                            "storage_quota_mb",
                            "plugin_quota",
                        )
                        if k in p and hasattr(BillingPlan, k)
                    },
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
        if hasattr(bal, "storage_limit_mb"):
            bal.storage_limit_mb = int(
                getattr(plan, "storage_quota_mb", None) or bal.storage_limit_mb or 1024
            )
        if hasattr(bal, "plugin_limit"):
            bal.plugin_limit = int(
                getattr(plan, "plugin_quota", None) or bal.plugin_limit or 10
            )
        await session.flush()
        return sub

    async def _resolve_limits(
        self, session: AsyncSession, actor: str
    ) -> tuple[int, int, int, int]:
        """Return (token, task, storage_mb, plugin) limits from plan or free."""
        sub = await self.get_active_subscription(session, actor)
        plan: BillingPlan | None = None
        if sub is not None:
            r = await session.execute(
                select(BillingPlan).where(BillingPlan.id == sub.plan_id)
            )
            plan = r.scalar_one_or_none()
        if plan is None:
            plan = await self.get_plan_by_code(session, "free")
        if plan:
            storage = int(getattr(plan, "storage_quota_mb", None) or 1024)
            plugins = int(getattr(plan, "plugin_quota", None) or 10)
            return plan.token_quota, plan.task_quota, storage, plugins
        return 50_000, 50, 500, 4

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
        if plan:
            token_limit, task_limit = plan.token_quota, plan.task_quota
            storage_limit = int(getattr(plan, "storage_quota_mb", None) or 1024)
            plugin_limit = int(getattr(plan, "plugin_quota", None) or 10)
        else:
            token_limit, task_limit, storage_limit, plugin_limit = (
                await self._resolve_limits(session, actor)
            )
        bal = QuotaBalance(
            id=str(uuid4()),
            actor=actor,
            period=period,
            token_used=0,
            token_limit=token_limit,
            task_used=0,
            task_limit=task_limit,
            storage_used_mb=0.0,
            storage_limit_mb=storage_limit,
            plugin_used=0,
            plugin_limit=plugin_limit,
        )
        session.add(bal)
        await session.flush()
        return bal

    async def get_quota(self, session: AsyncSession, actor: str) -> dict[str, Any]:
        await self.ensure_default_plans(session)
        bal = await self._get_or_create_balance(session, actor)
        sub = await self.get_active_subscription(session, actor)
        plan_code = None
        plan_obj: BillingPlan | None = None
        if sub:
            plan_obj = (
                await session.execute(
                    select(BillingPlan).where(BillingPlan.id == sub.plan_id)
                )
            ).scalar_one_or_none()
            plan_code = plan_obj.code if plan_obj else None
        if plan_code is None:
            free = await self.get_plan_by_code(session, "free")
            plan_obj = free
            plan_code = "free"
        return {
            "actor": actor,
            "period": bal.period,
            "token_used": bal.token_used,
            "token_limit": bal.token_limit,
            "task_used": bal.task_used,
            "task_limit": bal.task_limit,
            "storage_used_mb": getattr(bal, "storage_used_mb", 0) or 0,
            "storage_limit_mb": getattr(bal, "storage_limit_mb", 0) or 0,
            "plugin_used": getattr(bal, "plugin_used", 0) or 0,
            "plugin_limit": getattr(bal, "plugin_limit", 0) or 0,
            "plan_code": plan_code,
            "billing_cycle": getattr(plan_obj, "billing_cycle", None) or "monthly",
            "subscription_status": sub.status if sub else "none",
            "billing_enabled": billing_enabled(),
            "limits": {
                "tasks": bal.task_limit,
                "tokens": bal.token_limit,
                "storage_mb": getattr(bal, "storage_limit_mb", 0) or 0,
                "plugins": getattr(bal, "plugin_limit", 0) or 0,
            },
        }

    async def get_current_plan(
        self, session: AsyncSession, actor: str
    ) -> dict[str, Any]:
        """Current plan + quota snapshot for GET /billing/plan."""
        await self.ensure_default_plans(session)
        quota = await self.get_quota(session, actor)
        plan = await self.get_plan_by_code(session, quota.get("plan_code") or "free")
        return {
            "plan": {
                "id": plan.id if plan else None,
                "code": plan.code if plan else "free",
                "name": plan.name if plan else "Free",
                "description": plan.description if plan else "",
                "price_month_cents": plan.price_month_cents if plan else 0,
                "billing_cycle": getattr(plan, "billing_cycle", None) or "monthly",
                "token_quota": plan.token_quota if plan else quota["token_limit"],
                "task_quota": plan.task_quota if plan else quota["task_limit"],
                "storage_quota_mb": getattr(plan, "storage_quota_mb", None)
                or quota.get("storage_limit_mb"),
                "plugin_quota": getattr(plan, "plugin_quota", None)
                or quota.get("plugin_limit"),
                "features": (plan.features if plan else {}) or {},
            },
            "quota": quota,
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
                metric="task",
            )

    async def ensure_token_quota(
        self, session: AsyncSession, actor: str, *, quantity: float = 0
    ) -> None:
        if not billing_enabled():
            return
        bal = await self._get_or_create_balance(session, actor)
        if float(bal.token_used) + float(quantity) > float(bal.token_limit):
            raise QuotaExceededError(
                "Token quota exceeded for this billing period",
                detail={
                    "token_used": bal.token_used,
                    "token_limit": bal.token_limit,
                    "period": bal.period,
                },
                metric="token",
            )

    async def ensure_storage_quota(
        self, session: AsyncSession, actor: str, *, add_mb: float = 0
    ) -> None:
        if not billing_enabled():
            return
        bal = await self._get_or_create_balance(session, actor)
        used = float(getattr(bal, "storage_used_mb", 0) or 0)
        limit = float(getattr(bal, "storage_limit_mb", 0) or 0)
        if limit and used + float(add_mb) > limit:
            raise QuotaExceededError(
                "Storage quota exceeded for this billing period",
                detail={
                    "storage_used_mb": used,
                    "storage_limit_mb": limit,
                    "period": bal.period,
                },
                metric="storage",
            )

    async def ensure_plugin_quota(self, session: AsyncSession, actor: str) -> None:
        if not billing_enabled():
            return
        bal = await self._get_or_create_balance(session, actor)
        used = int(getattr(bal, "plugin_used", 0) or 0)
        limit = int(getattr(bal, "plugin_limit", 0) or 0)
        if limit and used >= limit:
            raise QuotaExceededError(
                "Plugin quota exceeded for this billing period",
                detail={
                    "plugin_used": used,
                    "plugin_limit": limit,
                    "period": bal.period,
                },
                metric="plugin",
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
            elif metric in {"storage", "storage_mb"}:
                bal.storage_used_mb = float(
                    getattr(bal, "storage_used_mb", 0) or 0
                ) + float(quantity)
            elif metric == "plugin":
                bal.plugin_used = int(getattr(bal, "plugin_used", 0) or 0) + int(
                    quantity
                )
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
        token_limit, task_limit, storage_limit, plugin_limit = (
            await self._resolve_limits(session, actor)
        )
        bal = QuotaBalance(
            id=str(uuid4()),
            actor=actor,
            period=period,
            token_used=0,
            token_limit=token_limit,
            task_used=0,
            task_limit=task_limit,
            storage_used_mb=0.0,
            storage_limit_mb=storage_limit,
            plugin_used=0,
            plugin_limit=plugin_limit,
        )
        session.add(bal)
        await session.flush()
        logger.info(
            "Quota rollover actor=%s period=%s limits token=%s task=%s storage=%s plugins=%s",
            actor,
            period,
            token_limit,
            task_limit,
            storage_limit,
            plugin_limit,
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
