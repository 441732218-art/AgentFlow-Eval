# (c) 2026 AgentFlow-Eval
"""SaaS billing models: plans, subscriptions, usage, quotas, invoices."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PKMixin, TenantMixin, TimestampMixin


class BillingPlan(PKMixin, TimestampMixin, Base):
    """Subscription plan catalog."""

    __tablename__ = "billing_plans"
    __table_args__ = (UniqueConstraint("code", name="uq_billing_plans_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_month_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=100_000)
    task_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    # Free-form feature flags, e.g. {"plugins": ["echo_tool"], "vision": true}
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subscription(PKMixin, TenantMixin, TimestampMixin, Base):
    """Actor/tenant subscription to a plan."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_actor_status", "actor", "status"),
        Index("ix_subscriptions_tenant_status", "tenant_id", "status"),
    )

    actor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active"
    )  # active|past_due|canceled|trialing
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)


class UsageRecord(PKMixin, TenantMixin, Base):
    """Immutable usage event (token / task / judge / storage)."""

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_actor_created", "actor", "created_at"),
        Index("ix_usage_metric_created", "metric", "created_at"),
        Index("ix_usage_trace_id", "trace_id"),
        Index("ix_usage_tenant_created", "tenant_id", "created_at"),
    )

    actor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)  # token|task|judge|storage
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ref_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class QuotaBalance(PKMixin, TimestampMixin, Base):
    """Period-scoped counters per actor."""

    __tablename__ = "quota_balances"
    __table_args__ = (
        UniqueConstraint("actor", "period", name="uq_quota_actor_period"),
        Index("ix_quota_actor_period", "actor", "period"),
    )

    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    # YYYY-MM
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    token_used: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    token_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100_000)
    task_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class Invoice(PKMixin, TenantMixin, TimestampMixin, Base):
    """Billing period invoice (draft until payment integration)."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_actor_period", "actor", "period"),
        Index("ix_invoices_tenant_period", "tenant_id", "period"),
    )

    actor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft"
    )  # draft|open|paid|void
    line_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
