# (c) 2026 AgentFlow-Eval
"""Lightweight audit trail for mutating operations."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("app.audit")


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    actor: str = "anonymous",
    detail: dict[str, Any] | None = None,
    request_id: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Persist an audit log row and emit structured log line.

    When ``request_id`` is omitted, falls back to the current TraceID contextvar
    so API → audit rows share the same correlation id.
    """
    if not request_id:
        try:
            from app.core.observability.tracing import get_trace_id

            request_id = get_trace_id() or None
        except Exception:
            request_id = None
    detail_map = dict(detail or {})
    if request_id and "trace_id" not in detail_map:
        detail_map["trace_id"] = request_id
    entry = AuditLog(
        actor=actor or "anonymous",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail_map,
        request_id=request_id,
        ip_address=ip,
    )
    session.add(entry)
    # Caller is responsible for commit (endpoint / get_db)
    logger.info(
        "audit action=%s resource=%s/%s actor=%s request_id=%s",
        action,
        resource_type,
        resource_id,
        actor,
        request_id,
    )
    return entry
