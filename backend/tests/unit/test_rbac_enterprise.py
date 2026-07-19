# (c) 2026 AgentFlow-Eval
"""Enterprise RBAC roles and permission matrix."""

from __future__ import annotations

from app.core.rbac import (
    CROSS_OWNER_ROLES,
    Permission,
    Role,
    has_permission,
    matrix_as_dict,
    permissions_for,
    resolve_role_for_actor,
)


class TestEnterpriseRoles:
    def test_enterprise_roles_present(self) -> None:
        assert Role.SYSTEM_ADMIN.value == "system_admin"
        assert Role.TENANT_ADMIN.value == "tenant_admin"
        assert Role.MEMBER.value == "member"
        assert Role.VIEWER.value == "viewer"

    def test_legacy_aliases_parse(self) -> None:
        assert Role.parse("admin") is Role.ADMIN
        assert Role.parse("user") is Role.USER
        assert Role.parse("guest") is Role.GUEST
        assert Role.parse("system_admin") is Role.SYSTEM_ADMIN
        assert Role.parse("member") is Role.MEMBER

    def test_canonical_mapping(self) -> None:
        assert Role.ADMIN.canonical() is Role.SYSTEM_ADMIN
        assert Role.USER.canonical() is Role.MEMBER
        assert Role.GUEST.canonical() is Role.VIEWER

    def test_system_admin_has_tenant_create(self) -> None:
        assert has_permission(Role.SYSTEM_ADMIN, Permission.TENANT_CREATE)
        assert has_permission(Role.ADMIN, Permission.TENANT_CREATE)
        assert not has_permission(Role.TENANT_ADMIN, Permission.TENANT_CREATE)
        assert has_permission(Role.TENANT_ADMIN, Permission.TENANT_MANAGE)

    def test_billing_and_benchmark_perms(self) -> None:
        assert has_permission(Role.TENANT_ADMIN, Permission.BILLING_MANAGE)
        assert has_permission(Role.MANAGER, Permission.BILLING_READ)
        assert not has_permission(Role.VIEWER, Permission.BILLING_MANAGE)
        assert has_permission(Role.MANAGER, Permission.BENCHMARK_CREATE)
        assert has_permission(Role.MEMBER, Permission.BENCHMARK_READ)
        assert not has_permission(Role.VIEWER, Permission.BENCHMARK_CREATE)

    def test_member_mirrors_legacy_user(self) -> None:
        assert permissions_for(Role.MEMBER) == permissions_for(Role.USER)

    def test_viewer_mirrors_legacy_guest(self) -> None:
        assert permissions_for(Role.VIEWER) == permissions_for(Role.GUEST)

    def test_cross_owner_roles(self) -> None:
        assert Role.SYSTEM_ADMIN in CROSS_OWNER_ROLES
        assert Role.TENANT_ADMIN in CROSS_OWNER_ROLES
        assert Role.MEMBER not in CROSS_OWNER_ROLES
        assert Role.VIEWER not in CROSS_OWNER_ROLES

    def test_matrix_includes_enterprise_keys(self) -> None:
        m = matrix_as_dict()
        assert "system_admin" in m
        assert "tenant_admin" in m
        assert "member" in m
        assert "viewer" in m
        assert Permission.TENANT_MANAGE.value in m["tenant_admin"]
        assert Permission.BILLING_READ.value in m["manager"]
