# (c) 2026 AgentFlow-Eval
"""API Key authentication helpers with optional RBAC role binding."""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass

from fastapi import Header, Request
from fastapi.security.utils import get_authorization_scheme_param

from app.config import settings
from app.core.rbac import Role, resolve_role_for_actor
from app.utils.exceptions import AgentFlowError


class UnauthorizedError(AgentFlowError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, status_code=401, detail=None)


@dataclass(frozen=True)
class ApiKeyEntry:
    """Parsed API key configuration entry."""

    secret: str
    actor: str
    role: Role | None = None  # None → resolve at auth time


@dataclass(frozen=True)
class AuthIdentity:
    """Authenticated principal derived from API key."""

    key_id: str
    actor: str
    raw_key_prefix: str
    role: Role = Role.USER


def parse_api_key_entries(raw: str | list[str] | None) -> list[ApiKeyEntry]:
    """Parse API_KEYS into structured entries.

    Supported formats per item:
    - ``secret``
    - ``secret:actor``
    - ``secret:actor:role``  (role is admin|manager|reviewer|user|guest)
    """
    if not raw:
        return []
    items: list[str]
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        items = [p.strip() for p in str(raw).split(",") if p.strip()]

    entries: list[ApiKeyEntry] = []
    for idx, item in enumerate(items, start=1):
        parts = [p.strip() for p in item.split(":")]
        secret = parts[0] if parts else ""
        if not secret:
            continue
        actor = parts[1] if len(parts) > 1 and parts[1] else f"key_{idx}"
        role: Role | None = None
        if len(parts) > 2 and parts[2]:
            try:
                role = Role.parse(parts[2])
            except ValueError:
                # Treat third segment as part of actor name if invalid role
                actor = f"{actor}:{parts[2]}"
                role = None
        entries.append(ApiKeyEntry(secret=secret, actor=actor, role=role))
    return entries


def parse_api_keys(raw: str | list[str] | None) -> dict[str, str]:
    """Parse API keys config into {secret: actor_name}.

    Backward-compatible helper used by settings UI and tests.
    """
    return {e.secret: e.actor for e in parse_api_key_entries(raw)}


def extract_api_key(
    request: Request,
    authorization: str | None = None,
    x_api_key: str | None = None,
) -> str | None:
    """Extract API key from X-API-Key or Authorization: Bearer."""
    key = (x_api_key or request.headers.get("X-API-Key") or "").strip()
    if key:
        return key
    header = authorization or request.headers.get("Authorization")
    if header:
        scheme, param = get_authorization_scheme_param(header)
        if scheme.lower() == "bearer" and param:
            return param.strip()
        # Also accept raw "ApiKey <token>"
        if scheme.lower() in {"apikey", "api-key"} and param:
            return param.strip()
    return None


def authenticate_api_key(api_key: str | None) -> AuthIdentity | None:
    """Validate API key against configured secrets (constant-time compare)."""
    if not api_key:
        return None
    entries = parse_api_key_entries(settings.API_KEYS)
    for entry in entries:
        if hmac.compare_digest(api_key, entry.secret):
            role = resolve_role_for_actor(entry.actor, explicit=entry.role)
            return AuthIdentity(
                key_id=secrets.token_hex(4),
                actor=entry.actor,
                raw_key_prefix=api_key[:4] + "***",
                role=role,
            )
    return None


def require_auth_if_enabled(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthIdentity | None:
    """FastAPI dependency: enforce API key when AUTH_ENABLED is true."""
    if not settings.AUTH_ENABLED:
        # Anonymous dev identity — full access when RBAC not enforced
        identity = AuthIdentity(
            key_id="dev",
            actor="anonymous",
            raw_key_prefix="dev",
            role=Role.SYSTEM_ADMIN,
        )
        request.state.actor = identity.actor
        request.state.auth = identity
        request.state.role = identity.role
        return identity

    api_key = extract_api_key(request, authorization, x_api_key)
    identity = authenticate_api_key(api_key)
    if identity is None:
        raise UnauthorizedError(
            "Invalid or missing API key. Provide X-API-Key or Authorization: Bearer <key>."
        )
    request.state.actor = identity.actor
    request.state.auth = identity
    request.state.role = identity.role
    return identity


# Paths that skip auth even when enabled
AUTH_PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        # Stripe webhook (verified by signature, not API key)
        "/api/v1/billing/webhook/stripe",
        "/api/v1/billing/webhook",
    }
)


def is_public_path(path: str) -> bool:
    """Return True if the path is exempt from API key authentication."""
    if path in AUTH_PUBLIC_PATHS:
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    if path.rstrip("/").endswith("/billing/webhook/stripe"):
        return True
    if path.rstrip("/").endswith("/billing/webhook"):
        return True
    return False
