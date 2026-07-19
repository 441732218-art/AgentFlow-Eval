# (c) 2026 AgentFlow-Eval
"""Enterprise multi-tenant models: tenants + membership."""

from __future__ import annotations

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PKMixin, TimestampMixin


class Tenant(PKMixin, TimestampMixin, Base):
    """Organization / workspace boundary for SaaS and private multi-team deploys."""

    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_tenants_slug"),
        Index("ix_tenants_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active"
    )  # active|suspended|deleted
    plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<Tenant {self.slug} status={self.status}>"


class TenantMember(PKMixin, TimestampMixin, Base):
    """Actor membership inside a tenant (role is tenant-scoped RBAC)."""

    __tablename__ = "tenant_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_member"),
        Index("ix_tenant_members_user", "user_id"),
        Index("ix_tenant_members_tenant_role", "tenant_id", "role"),
    )

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Maps to API-key actor name (no separate users table in v1)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="member",
    )  # tenant_admin|manager|reviewer|member|viewer

    def __repr__(self) -> str:
        return f"<TenantMember {self.user_id}@{self.tenant_id} role={self.role}>"
