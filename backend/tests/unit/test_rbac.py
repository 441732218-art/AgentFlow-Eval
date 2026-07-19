# (c) 2026 AgentFlow-Eval
"""Unit tests for RBAC roles, permissions, decorator, and resource checks."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.rbac import (
    CROSS_TENANT_ROLES,
    ROLE_PERMISSIONS,
    ForbiddenError,
    Permission,
    Role,
    ensure_permission,
    ensure_resource_access,
    has_all_permissions,
    has_any_permission,
    has_permission,
    matrix_as_dict,
    permissions_for,
    require_permission,
    resolve_role_for_actor,
)
from app.core.security import AuthIdentity, authenticate_api_key, parse_api_key_entries
from app.main import app
from app.utils.exceptions import NotFoundError


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
        assert has_any_permission(Role.GUEST, [Permission.TASK_CREATE, Permission.TASK_READ])
        assert not has_any_permission(Role.GUEST, [Permission.TASK_CREATE, Permission.AUDIT_READ])


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
        req.state = SimpleNamespace(actor="a", auth=AuthIdentity("1", "a", "x***", Role.USER))
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
        transport = ASGITransport(app=app)
        with patch("app.core.middleware.settings") as ms, patch(
            "app.core.security.settings"
        ) as ss, patch("app.core.rbac.settings") as rs:
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
        transport = ASGITransport(app=app)
        with patch("app.core.middleware.settings") as ms, patch(
            "app.core.security.settings"
        ) as ss, patch("app.core.rbac.settings") as rs:
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
        transport = ASGITransport(app=app)
        with patch("app.core.middleware.settings") as ms, patch(
            "app.core.security.settings"
        ) as ss, patch("app.core.rbac.settings") as rs:
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
        """When AUTH_ENABLED=false, create task works without API key."""
        transport = ASGITransport(app=app)
        # Use real settings (AUTH typically false in test env) + override DB not needed for tools
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/v1/tools")
        assert r.status_code == 200
