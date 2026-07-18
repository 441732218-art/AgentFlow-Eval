# (c) 2026 AgentFlow-Eval
"""Current actor identity + permission set (frontend RBAC contract)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.config import settings
from app.core.rbac import (
    get_request_role,
    permissions_for,
    rbac_enforced,
)
from app.core.profiles import profile_status

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


@router.get("")
async def get_me(request: Request) -> dict[str, Any]:
    """Return actor, role, permissions, and deploy profile summary.

    Frontend uses this for RouteGuard, dynamic menus, and button-level ``Can``.
    When AUTH is off, role is admin-equivalent so local demos stay frictionless.
    """
    actor = _actor(request)
    role = get_request_role(request)
    perms = sorted(p.value for p in permissions_for(role))
    status = {}
    try:
        status = profile_status()
    except Exception:
        status = {}

    return {
        "actor": actor,
        "role": role.value if hasattr(role, "value") else str(role),
        "permissions": perms,
        "rbac_enforced": rbac_enforced(),
        "auth_enabled": bool(getattr(settings, "AUTH_ENABLED", False)),
        "billing_enabled": bool(getattr(settings, "BILLING_ENABLED", False)),
        "deploy": status,
        "request_id": getattr(request.state, "request_id", None),
    }


@router.get("/permissions")
async def list_my_permissions(request: Request) -> dict[str, Any]:
    """Permission strings only (lightweight poll)."""
    role = get_request_role(request)
    perms = sorted(p.value for p in permissions_for(role))
    return {
        "role": role.value if hasattr(role, "value") else str(role),
        "permissions": perms,
        "rbac_enforced": rbac_enforced(),
    }
