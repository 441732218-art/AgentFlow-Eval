# (c) 2026 AgentFlow-Eval
"""Unit tests for RBAC roles, permissions, decorator, and resource checks."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncIterator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.config import settings
from app.core import dependencies as deps
from app.core.dependencies import get_db
from app.core.rbac import (
    CROSS_TENANT_ROLES,
    ForbiddenError,
    Permission,
    Role,
    ensure_permission,
    ensure_resource_access,
    has_all_permissions,
    has_any_permission,
    has_permission,
    matrix_as_dict,
    require_permission,
    resolve_role_for_actor,
)
from app.core.security import AuthIdentity, authenticate_api_key, parse_api_key_entries
from app.main import app
from app.utils.exceptions import NotFoundError

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@asynccontextmanager
async def _aols_sink_disabled() -> AsyncIterator[None]:
    """Disable AOLS DB sink for ASGI calls that do not override get_db (E15a)."""
    from app.core.observability.aols.sinks import db as aols_db_sink

    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))
    settings.LOG_DB_SINK = False
    try:
        yield
    finally:
        try:
            with aols_db_sink._lock:
                aols_db_sink._queue.clear()
        except Exception:
            pass
        settings.LOG_DB_SINK = prev_sink


@asynccontextmanager
async def _isolated_task_post_db() -> AsyncIterator[None]:
    """UUID temp SQLite + get_db override for POST /tasks (E15a).

    FastAPI resolves Depends(get_db) before require_permission raises 403, so the
    default async_session_factory would open agentflow_eval.db without this.
    Restores only the get_db override entry (does not clear all overrides).
    """
    from app.core.observability.aols.sinks import db as aols_db_sink

    db_path = _BACKEND_ROOT / f"test_rbac_e15a_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert "test_tasks_unit.db" not in test_db_url

    if db_path.exists():
        db_path.unlink()

    engine = create_async_engine(test_db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override() -> Any:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    had_get_db = get_db in app.dependency_overrides
    prev_get_db = app.dependency_overrides.get(get_db)
    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))

    deps.engine = engine
    deps.async_session_factory = factory
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = False
    app.dependency_overrides[get_db] = _override
    try:
        yield
    finally:
        if had_get_db:
            app.dependency_overrides[get_db] = prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)
        try:
            with aols_db_sink._lock:
                aols_db_sink._queue.clear()
        except Exception:
            pass
        settings.LOG_DB_SINK = prev_sink
        settings.DATABASE_URL = prev_db_url
        deps.engine = prev_engine
        deps.async_session_factory = prev_factory
        await engine.dispose()
        try:
            if db_path.exists():
                db_path.unlink()
        except OSError:
            pass


class TestRolePermissionMatrix:
    def test_all_roles_defined(self) -> None:
        # Enterprise + legacy aliases
        assert {
            Role.SYSTEM_ADMIN,
            Role.TENANT_ADMIN,
            Role.MANAGER,
            Role.REVIEWER,
            Role.MEMBER,
            Role.VIEWER,
            Role.ADMIN,
            Role.USER,
            Role.GUEST,
        }.issubset(set(Role))

    def test_admin_has_all(self) -> None:
        for perm in Permission:
            assert has_permission(Role.ADMIN, perm)
            assert has_permission(Role.SYSTEM_ADMIN, perm)

    def test_guest_read_only(self) -> None:
        assert has_permission(Role.GUEST, Permission.TASK_READ)
        assert has_permission(Role.GUEST, Permission.EVALUATION_READ)
        assert not has_permission(Role.GUEST, Permission.TASK_CREATE)
        assert not has_permission(Role.GUEST, Permission.TASK_EXECUTE)
        assert not has_permission(Role.GUEST, Permission.AUDIT_READ)

    def test_user_task_ops_no_audit(self) -> None:
        assert has_all_permissions(
            Role.USER,
            [
                Permission.TASK_CREATE,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
                Permission.TASK_DELETE,
                Permission.TASK_EXECUTE,
                Permission.TASK_CANCEL,
                Permission.EVALUATION_READ,
                Permission.EVALUATION_SUBMIT,
            ],
        )
        assert not has_permission(Role.USER, Permission.AUDIT_READ)
        assert not has_permission(Role.USER, Permission.EVALUATION_APPROVE)
        assert not has_permission(Role.USER, Permission.SYSTEM_CONFIG)

    def test_reviewer_approve(self) -> None:
        assert has_permission(Role.REVIEWER, Permission.EVALUATION_APPROVE)
        assert has_permission(Role.REVIEWER, Permission.TASK_READ)
        assert not has_permission(Role.REVIEWER, Permission.TASK_DELETE)

    def test_manager_audit_no_user_manage(self) -> None:
        assert has_permission(Role.MANAGER, Permission.AUDIT_READ)
        assert has_permission(Role.MANAGER, Permission.TASK_EXECUTE)
        assert not has_permission(Role.MANAGER, Permission.USER_MANAGE)
        assert not has_permission(Role.MANAGER, Permission.SYSTEM_CONFIG)

    def test_matrix_export(self) -> None:
        m = matrix_as_dict()
        assert "admin" in m
        assert "user" in m or "member" in m
        # legacy user or enterprise member both hold task:create
        create_roles = [k for k, v in m.items() if Permission.TASK_CREATE.value in v]
        assert "user" in create_roles or "member" in create_roles

    def test_has_any(self) -> None:
        assert has_any_permission(
            Role.GUEST, [Permission.TASK_CREATE, Permission.TASK_READ]
        )
        assert not has_any_permission(
            Role.GUEST, [Permission.TASK_CREATE, Permission.AUDIT_READ]
        )


class TestEnsurePermission:
    def test_skipped_when_rbac_off(self) -> None:
        with patch("app.core.rbac.rbac_enforced", return_value=False):
            ensure_permission(Role.GUEST, Permission.SYSTEM_CONFIG)  # no raise

    def test_raises_403_when_denied(self) -> None:
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            with pytest.raises(ForbiddenError) as exc:
                ensure_permission(Role.GUEST, Permission.TASK_DELETE)
            assert exc.value.status_code == 403


class TestResourceAccess:
    def test_owner_ok(self) -> None:
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            ensure_resource_access(
                role=Role.USER,
                actor="alice",
                owner="alice",
                permission=Permission.TASK_UPDATE,
            )

    def test_cross_tenant_manager(self) -> None:
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            ensure_resource_access(
                role=Role.MANAGER,
                actor="mgr",
                owner="alice",
                permission=Permission.TASK_READ,
            )

    def test_user_foreign_hidden(self) -> None:
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            with pytest.raises(NotFoundError):
                ensure_resource_access(
                    role=Role.USER,
                    actor="alice",
                    owner="bob",
                    permission=Permission.TASK_READ,
                    resource="Task",
                    resource_id="t1",
                    hide_existence=True,
                )

    def test_reviewer_cross_tenant(self) -> None:
        assert Role.REVIEWER in CROSS_TENANT_ROLES
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            ensure_resource_access(
                role=Role.REVIEWER,
                actor="rev",
                owner="alice",
                permission=Permission.TASK_READ,
            )


class TestApiKeyRoles:
    def test_parse_entries_with_role(self) -> None:
        entries = parse_api_key_entries("s1:alice:manager,s2:bob:guest")
        assert entries[0].actor == "alice"
        assert entries[0].role == Role.MANAGER
        assert entries[1].role == Role.GUEST

    def test_authenticate_embeds_role(self) -> None:
        with patch("app.core.security.settings") as s:
            s.API_KEYS = "secret:ops:manager"
            s.ADMIN_ACTORS = "admin"
            s.ACTOR_ROLES = ""
            s.DEFAULT_ROLE = "user"
            with patch("app.core.rbac.settings", s):
                ident = authenticate_api_key("secret")
        assert ident is not None
        assert ident.actor == "ops"
        assert ident.role == Role.MANAGER

    def test_admin_actors_default_role(self) -> None:
        with patch("app.core.rbac.settings") as s:
            s.ADMIN_ACTORS = "root"
            s.ACTOR_ROLES = ""
            s.DEFAULT_ROLE = "user"
            with patch("app.core.tenancy.settings", s):
                # ADMIN_ACTORS resolve to enterprise system_admin
                assert resolve_role_for_actor("root") == Role.SYSTEM_ADMIN
                # DEFAULT_ROLE=user → legacy USER (same perms as MEMBER)
                assert resolve_role_for_actor("nobody") == Role.USER


class TestRequirePermissionDecorator:
    @pytest.mark.asyncio
    async def test_async_allows(self) -> None:
        @require_permission(Permission.TASK_READ)
        async def handler(request: Request) -> dict:
            return {"ok": True}

        req = MagicMock(spec=Request)
        req.state = SimpleNamespace(
            actor="a", auth=AuthIdentity("1", "a", "x***", Role.USER)
        )
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            out = await handler(req)
        assert out["ok"] is True

    @pytest.mark.asyncio
    async def test_async_denies(self) -> None:
        @require_permission(Permission.SYSTEM_CONFIG)
        async def handler(request: Request) -> dict:
            return {"ok": True}

        req = MagicMock(spec=Request)
        req.state = SimpleNamespace(
            actor="g", auth=AuthIdentity("1", "g", "x***", Role.GUEST)
        )
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            with pytest.raises(ForbiddenError):
                await handler(req)

    def test_sync_decorator(self) -> None:
        @require_permission(Permission.TASK_READ)
        def handler(request: Request) -> str:
            return "ok"

        req = MagicMock(spec=Request)
        req.state = SimpleNamespace(
            actor="u", auth=AuthIdentity("1", "u", "x***", Role.USER)
        )
        with patch("app.core.rbac.rbac_enforced", return_value=True):
            assert handler(req) == "ok"


class TestApiIntegration:
    @pytest.mark.asyncio
    async def test_guest_cannot_create_task(self) -> None:
        # POST /tasks Declares Depends(get_db); FastAPI opens a session before 403.
        async with _isolated_task_post_db():
            transport = ASGITransport(app=app)
            with (
                patch("app.core.middleware.settings") as ms,
                patch("app.core.security.settings") as ss,
                patch("app.core.rbac.settings") as rs,
            ):
                for s in (ms, ss, rs):
                    s.AUTH_ENABLED = True
                    s.RBAC_ENABLED = True
                    s.API_KEYS = "gk:guest1:guest"
                    s.ADMIN_ACTORS = "admin"
                    s.ACTOR_ROLES = ""
                    s.DEFAULT_ROLE = "user"
                async with AsyncClient(transport=transport, base_url="http://test") as c:
                    denied = await c.post(
                        "/api/v1/tasks",
                        json={"name": "x", "description": "", "agent_config": {}},
                        headers={"X-API-Key": "gk"},
                    )
        assert denied.status_code == 403

    @pytest.mark.asyncio
    async def test_user_can_list_tools(self) -> None:
        # /tools has no get_db; disable AOLS sink so logging cannot touch default DB.
        async with _aols_sink_disabled():
            transport = ASGITransport(app=app)
            with (
                patch("app.core.middleware.settings") as ms,
                patch("app.core.security.settings") as ss,
                patch("app.core.rbac.settings") as rs,
            ):
                for s in (ms, ss, rs):
                    s.AUTH_ENABLED = True
                    s.RBAC_ENABLED = True
                    s.API_KEYS = "uk:alice:user"
                    s.ADMIN_ACTORS = "admin"
                    s.ACTOR_ROLES = ""
                    s.DEFAULT_ROLE = "user"
                async with AsyncClient(transport=transport, base_url="http://test") as c:
                    ok = await c.get("/api/v1/tools", headers={"X-API-Key": "uk"})
        assert ok.status_code == 200

    @pytest.mark.asyncio
    async def test_guest_cannot_probe_tool(self) -> None:
        # /tools/probe has no get_db; AOLS sink disabled for default-DB safety.
        async with _aols_sink_disabled():
            transport = ASGITransport(app=app)
            with (
                patch("app.core.middleware.settings") as ms,
                patch("app.core.security.settings") as ss,
                patch("app.core.rbac.settings") as rs,
            ):
                for s in (ms, ss, rs):
                    s.AUTH_ENABLED = True
                    s.RBAC_ENABLED = True
                    s.API_KEYS = "gk:guest1:guest"
                    s.ADMIN_ACTORS = "admin"
                    s.ACTOR_ROLES = ""
                    s.DEFAULT_ROLE = "user"
                async with AsyncClient(transport=transport, base_url="http://test") as c:
                    r = await c.post(
                        "/api/v1/tools/probe",
                        json={"name": "calculator", "args": {"expression": "1+1"}},
                        headers={"X-API-Key": "gk"},
                    )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_auth_off_skips_rbac(self) -> None:
        """When AUTH_ENABLED=false, tools list works without API key."""
        async with _aols_sink_disabled():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/v1/tools")
        assert r.status_code == 200
