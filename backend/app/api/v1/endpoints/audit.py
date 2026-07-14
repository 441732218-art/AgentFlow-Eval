# (c) 2026 AgentFlow-Eval
"""Audit log query API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List recent audit events (newest first)."""
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)

    total = (await session.execute(count_query)).scalar() or 0
    result = await session.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.scalars().all()
    items = [
        {
            "id": r.id,
            "actor": r.actor,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "detail": r.detail,
            "request_id": r.request_id,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
