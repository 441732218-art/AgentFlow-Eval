# (c) 2026 AgentFlow-Eval
"""Enterprise tenant management API."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.rbac import Permission, get_request_role, require_permission
from app.core.tenant_context import (
    extract_tenant_header,
    multi_tenant_enabled,
    resolve_tenant_context,
    tenant_dict,
)
from app.models.tenant import Tenant, TenantMember
from app.utils.exceptions import AgentFlowError, NotFoundError

router = APIRouter()

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,62}[a-z0-9])?$")


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100)
    plan_id: str | None = None


class TenantMemberAdd(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="member", max_length=32)


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    plan_id: str | None = None


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


def _slugify(raw: str) -> str:
    s = raw.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:64] or "tenant"


@router.get("/context")
async def tenant_context(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Current multi-tenant resolution (header + membership)."""
    role = get_request_role(request)
    await resolve_tenant_context(
        session,
        actor=_actor(request),
        header_value=extract_tenant_header(request),
        system_role=role.value,
    )
    return tenant_dict()


@router.get("")
@require_permission(Permission.TENANT_MANAGE, Permission.TASK_READ, require_all=False)
async def list_tenants(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List tenants visible to the caller.

    system_admin: all tenants.
    others: memberships only.
    """
    actor = _actor(request)
    role = get_request_role(request)
    if role.value in {"system_admin", "admin"}:
        rows = (
            await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))
        ).scalars().all()
    else:
        q = (
            select(Tenant)
            .join(TenantMember, TenantMember.tenant_id == Tenant.id)
            .where(TenantMember.user_id == actor)
            .order_by(Tenant.created_at.desc())
        )
        rows = (await session.execute(q)).scalars().all()
    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "status": t.status,
                "plan_id": t.plan_id,
            }
            for t in rows
        ],
        "multi_tenant_enabled": multi_tenant_enabled(),
    }


@router.post("", status_code=201)
@require_permission(Permission.TENANT_CREATE)
async def create_tenant(
    body: TenantCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a tenant; creator becomes tenant_admin member."""
    slug = _slugify(body.slug or body.name)
    if not _SLUG_RE.match(slug):
        raise AgentFlowError(
            message="Invalid tenant slug",
            status_code=422,
            detail="slug must be 2-64 chars [a-z0-9-]",
        )
    exists = await session.execute(select(Tenant).where(Tenant.slug == slug))
    if exists.scalar_one_or_none():
        raise AgentFlowError(
            message="Tenant slug already exists",
            status_code=409,
            detail=slug,
        )

    actor = _actor(request)
    tenant = Tenant(
        id=str(uuid4()),
        name=body.name.strip(),
        slug=slug,
        status="active",
        plan_id=body.plan_id,
    )
    session.add(tenant)
    session.add(
        TenantMember(
            id=str(uuid4()),
            tenant_id=tenant.id,
            user_id=actor,
            role="tenant_admin",
        )
    )
    await session.flush()
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "plan_id": tenant.plan_id,
        "member_role": "tenant_admin",
    }


@router.get("/{tenant_id}")
@require_permission(Permission.TASK_READ)
async def get_tenant(
    tenant_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get tenant if caller is member or system_admin."""
    role = get_request_role(request)
    result = await session.execute(
        select(Tenant).where((Tenant.id == tenant_id) | (Tenant.slug == tenant_id))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant", tenant_id)

    if role.value not in {"system_admin", "admin"}:
        mem = await session.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant.id,
                TenantMember.user_id == _actor(request),
            )
        )
        if mem.scalar_one_or_none() is None:
            raise NotFoundError("Tenant", tenant_id)

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "plan_id": tenant.plan_id,
    }


@router.post("/{tenant_id}/members", status_code=201)
@require_permission(Permission.TENANT_MANAGE)
async def add_member(
    tenant_id: str,
    body: TenantMemberAdd,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add or update a tenant member (tenant_admin / system_admin)."""
    result = await session.execute(
        select(Tenant).where((Tenant.id == tenant_id) | (Tenant.slug == tenant_id))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant", tenant_id)

    # Membership check unless system_admin
    role = get_request_role(request)
    if role.value not in {"system_admin", "admin"}:
        mem = await session.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant.id,
                TenantMember.user_id == _actor(request),
            )
        )
        m = mem.scalar_one_or_none()
        if m is None or m.role not in {"tenant_admin", "manager"}:
            raise AgentFlowError(
                message="Only tenant_admin/manager can add members",
                status_code=403,
            )

    allowed = {
        "tenant_admin",
        "manager",
        "reviewer",
        "member",
        "viewer",
        "user",
        "guest",
    }
    member_role = body.role.strip().lower()
    if member_role not in allowed:
        raise AgentFlowError(
            message="Invalid member role",
            status_code=422,
            detail=sorted(allowed),
        )
    # Normalize legacy
    if member_role == "user":
        member_role = "member"
    if member_role == "guest":
        member_role = "viewer"

    existing = await session.execute(
        select(TenantMember).where(
            TenantMember.tenant_id == tenant.id,
            TenantMember.user_id == body.user_id.strip(),
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        row.role = member_role
        await session.flush()
        return {
            "tenant_id": tenant.id,
            "user_id": row.user_id,
            "role": row.role,
            "updated": True,
        }

    row = TenantMember(
        id=str(uuid4()),
        tenant_id=tenant.id,
        user_id=body.user_id.strip(),
        role=member_role,
    )
    session.add(row)
    await session.flush()
    return {
        "tenant_id": tenant.id,
        "user_id": row.user_id,
        "role": row.role,
        "updated": False,
    }


@router.get("/{tenant_id}/members")
@require_permission(Permission.TENANT_MANAGE, Permission.TASK_READ, require_all=False)
async def list_members(
    tenant_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await session.execute(
        select(Tenant).where((Tenant.id == tenant_id) | (Tenant.slug == tenant_id))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant", tenant_id)

    rows = (
        await session.execute(
            select(TenantMember).where(TenantMember.tenant_id == tenant.id)
        )
    ).scalars().all()
    return {
        "tenant_id": tenant.id,
        "items": [
            {"user_id": m.user_id, "role": m.role, "id": m.id} for m in rows
        ],
    }
