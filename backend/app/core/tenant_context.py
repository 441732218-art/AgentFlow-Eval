# (c) 2026 AgentFlow-Eval
"""Request-scoped enterprise TenantContext (X-Tenant-ID)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.exceptions import AgentFlowError, NotFoundError

_tenant_ctx: ContextVar["TenantContext | None"] = ContextVar("tenant_ctx", default=None)


class TenantAccessError(AgentFlowError):
    """Caller not allowed for the requested tenant."""

    def __init__(self, message: str = "Tenant access denied") -> None:
        super().__init__(message=message, status_code=403, detail=None)


@dataclass(frozen=True)
class TenantContext:
    """Resolved tenant for the current request."""

    tenant_id: str | None
    tenant_slug: str | None
    member_role: str | None
    enforced: bool

    @property
    def active(self) -> bool:
        return bool(self.tenant_id)


def multi_tenant_enabled() -> bool:
    """Enterprise multi-tenant mode (org tables + X-Tenant-ID)."""
    return bool(getattr(settings, "MULTI_TENANT_ENABLED", False))


def get_tenant_context() -> TenantContext | None:
    return _tenant_ctx.get()


def set_tenant_context(ctx: TenantContext | None) -> None:
    _tenant_ctx.set(ctx)


def current_tenant_id() -> str | None:
    ctx = get_tenant_context()
    return ctx.tenant_id if ctx else None


def extract_tenant_header(request: Request) -> str | None:
    """Accept X-Tenant-ID (uuid or slug)."""
    raw = (
        request.headers.get("X-Tenant-ID")
        or request.headers.get("X-Tenant-Id")
        or request.headers.get("x-tenant-id")
        or ""
    ).strip()
    return raw or None


async def resolve_tenant_context(
    session: AsyncSession,
    *,
    actor: str,
    header_value: str | None,
    system_role: str | None = None,
) -> TenantContext:
    """Resolve and validate tenant membership for ``actor``.

    - MULTI_TENANT off → empty context (legacy actor isolation only)
    - Header absent → empty tenant_id (optional scope)
    - Header present → must be valid tenant + membership (unless system_admin)
    """
    if not multi_tenant_enabled():
        ctx = TenantContext(
            tenant_id=None,
            tenant_slug=None,
            member_role=None,
            enforced=False,
        )
        set_tenant_context(ctx)
        return ctx

    if not header_value:
        ctx = TenantContext(
            tenant_id=None,
            tenant_slug=None,
            member_role=None,
            enforced=True,
        )
        set_tenant_context(ctx)
        return ctx

    from app.models.tenant import Tenant, TenantMember

    # Lookup by id or slug
    result = await session.execute(
        select(Tenant).where(
            (Tenant.id == header_value) | (Tenant.slug == header_value)
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant is None or tenant.status == "deleted":
        raise NotFoundError("Tenant", header_value)
    if tenant.status == "suspended":
        raise TenantAccessError("Tenant is suspended")

    # system_admin / legacy admin bypass membership
    role_l = (system_role or "").lower()
    if role_l in {"system_admin", "admin"}:
        ctx = TenantContext(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            member_role="system_admin",
            enforced=True,
        )
        set_tenant_context(ctx)
        return ctx

    mem = await session.execute(
        select(TenantMember).where(
            TenantMember.tenant_id == tenant.id,
            TenantMember.user_id == actor,
        )
    )
    member = mem.scalar_one_or_none()
    if member is None:
        raise TenantAccessError(
            f"Actor {actor!r} is not a member of tenant {tenant.slug!r}"
        )

    ctx = TenantContext(
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        member_role=member.role,
        enforced=True,
    )
    set_tenant_context(ctx)
    return ctx


def apply_tenant_filter(query: Any, model: Any, tenant_id: str | None = None) -> Any:
    """Restrict query to a single tenant when multi-tenant is active and scoped.

    Rows with ``tenant_id IS NULL`` are treated as legacy (visible only when
    filter is not enforced, or to system paths that opt out).
    """
    tid = tenant_id if tenant_id is not None else current_tenant_id()
    if not multi_tenant_enabled() or not tid:
        return query
    col = getattr(model, "tenant_id", None)
    if col is None:
        return query
    return query.where(col == tid)


def ensure_tenant_resource(
    resource_tenant_id: str | None,
    *,
    resource: str = "Resource",
    resource_id: str = "",
) -> None:
    """Raise NotFound if resource belongs to another tenant (no existence leak)."""
    if not multi_tenant_enabled():
        return
    tid = current_tenant_id()
    if not tid:
        return
    # Legacy unscoped rows: deny when a tenant is selected
    if not resource_tenant_id or resource_tenant_id != tid:
        raise NotFoundError(resource, resource_id)


def tenant_dict() -> dict[str, Any]:
    ctx = get_tenant_context()
    if not ctx:
        return {
            "multi_tenant_enabled": multi_tenant_enabled(),
            "tenant_id": None,
            "tenant_slug": None,
            "member_role": None,
        }
    return {
        "multi_tenant_enabled": multi_tenant_enabled(),
        "tenant_id": ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "member_role": ctx.member_role,
        "enforced": ctx.enforced,
    }
