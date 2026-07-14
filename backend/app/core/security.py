# (c) 2026 AgentFlow-Eval
"""API Key authentication helpers."""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass

from fastapi import Header, Request
from fastapi.security.utils import get_authorization_scheme_param

from app.config import settings
from app.utils.exceptions import AgentFlowError


class UnauthorizedError(AgentFlowError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, status_code=401, detail=None)


@dataclass(frozen=True)
class AuthIdentity:
    """Authenticated principal derived from API key."""

    key_id: str
    actor: str
    raw_key_prefix: str


def parse_api_keys(raw: str | list[str] | None) -> dict[str, str]:
    """Parse API keys config into {secret: actor_name}.

    Supported formats:
    - "secret1,secret2"  -> actors key_1, key_2
    - "secret1:alice,secret2:bob"
    - JSON list via pydantic already as list[str]
    """
    if not raw:
        return {}
    items: list[str]
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        items = [p.strip() for p in str(raw).split(",") if p.strip()]

    mapping: dict[str, str] = {}
    for idx, item in enumerate(items, start=1):
        if ":" in item:
            secret, actor = item.split(":", 1)
            secret, actor = secret.strip(), actor.strip() or f"key_{idx}"
        else:
            secret, actor = item, f"key_{idx}"
        if secret:
            mapping[secret] = actor
    return mapping


def extract_api_key(request: Request, authorization: str | None = None, x_api_key: str | None = None) -> str | None:
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
    keys = parse_api_keys(settings.API_KEYS)
    for secret, actor in keys.items():
        if hmac.compare_digest(api_key, secret):
            return AuthIdentity(
                key_id=secrets.token_hex(4),
                actor=actor,
                raw_key_prefix=api_key[:4] + "***",
            )
    return None


def require_auth_if_enabled(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthIdentity | None:
    """FastAPI dependency: enforce API key when AUTH_ENABLED is true."""
    if not settings.AUTH_ENABLED:
        # Anonymous dev identity
        return AuthIdentity(key_id="dev", actor="anonymous", raw_key_prefix="dev")

    api_key = extract_api_key(request, authorization, x_api_key)
    identity = authenticate_api_key(api_key)
    if identity is None:
        raise UnauthorizedError("Invalid or missing API key. Provide X-API-Key or Authorization: Bearer <key>.")
    request.state.actor = identity.actor
    request.state.auth = identity
    return identity


# Paths that skip auth even when enabled
AUTH_PUBLIC_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})
