# (c) 2026 AgentFlow-Eval
"""Audit log model for security-relevant actions."""

from sqlalchemy import Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PKMixin, TenantMixin, TimestampMixin


class AuditLog(PKMixin, TenantMixin, TimestampMixin, Base):
    """Immutable-style audit record (no update API)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_actor_created", "actor", "created_at"),
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="anonymous",
        comment="操作者标识",
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="动作，如 task.create / task.execute",
    )
    resource_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="资源类型",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="资源 ID",
    )
    detail: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="附加详情",
    )
    request_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="请求追踪 ID",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="客户端 IP",
    )
    note: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="备注",
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}/{self.resource_id}>"
