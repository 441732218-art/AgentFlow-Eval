# (c) 2026 AgentFlow-Eval
"""Settings / identity endpoints for the frontend Settings page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.core.security import authenticate_api_key, extract_api_key, parse_api_keys
from app.core.tenancy import admin_actors, is_admin, tenancy_enforced

router = APIRouter()


class ActorInfoResponse(BaseModel):
    """Current authenticated actor and admin flag."""

    current_actor: str = Field(..., description="Resolved actor name")
    is_admin: bool = Field(..., description="Whether actor is in ADMIN_ACTORS")
    auth_enabled: bool = Field(..., description="Whether API key auth is enforced")
    tenancy_enabled: bool = Field(..., description="Whether task isolation is active")
    available_actors: list[str] = Field(
        default_factory=list,
        description="Known actors from API_KEYS config (names only, not secrets)",
    )
    admin_actors: list[str] = Field(default_factory=list)
    api_key_configured: bool = Field(
        False, description="Whether a key was present on this request"
    )
    key_prefix: str | None = Field(
        None, description="Masked prefix of the presented key"
    )


@router.get("/actor", response_model=ActorInfoResponse)
async def get_current_actor(request: Request) -> Any:
    """Return identity derived from X-API-Key / Bearer token + settings.

    When AUTH_ENABLED is false, actor defaults to request.state.actor or 'anonymous'.
    """
    raw_key = extract_api_key(request)
    identity = authenticate_api_key(raw_key) if raw_key else None

    if identity is not None:
        actor = identity.actor
        key_prefix = identity.raw_key_prefix
        key_configured = True
    else:
        actor = getattr(request.state, "actor", None) or "anonymous"
        key_prefix = None
        key_configured = bool(raw_key)

    # Known actor labels from API_KEYS (never expose secrets)
    known = sorted(set(parse_api_keys(settings.API_KEYS).values()))
    admins = sorted(admin_actors())

    return ActorInfoResponse(
        current_actor=actor,
        is_admin=is_admin(actor),
        auth_enabled=bool(settings.AUTH_ENABLED),
        tenancy_enabled=tenancy_enforced(),
        available_actors=known,
        admin_actors=admins,
        api_key_configured=key_configured,
        key_prefix=key_prefix,
    )


class SettingsPublicResponse(BaseModel):
    """Non-secret public settings snapshot for UI."""

    app_name: str
    env: str
    auth_enabled: bool
    tenancy_enabled: bool
    admin_actors: list[str]
    available_actors: list[str]


@router.get("", response_model=SettingsPublicResponse)
async def get_public_settings() -> Any:
    """Public settings (no secrets)."""
    return SettingsPublicResponse(
        app_name=settings.APP_NAME,
        env=settings.ENV,
        auth_enabled=bool(settings.AUTH_ENABLED),
        tenancy_enabled=tenancy_enforced(),
        admin_actors=sorted(admin_actors()),
        available_actors=sorted(set(parse_api_keys(settings.API_KEYS).values())),
    )
