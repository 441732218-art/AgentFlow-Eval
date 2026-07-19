# (c) 2026 AgentFlow-Eval
"""Enterprise multi-tenant isolation tests (Tenant A cannot access Tenant B)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.tenant_context import (
    TenantAccessError,
    apply_tenant_filter,
    ensure_tenant_resource,
    multi_tenant_enabled,
    set_tenant_context,
    TenantContext,
    current_tenant_id,
)
from app.core.tenancy import can_access_task, apply_owner_filter
from app.models.task import Task, TaskStatus
from app.models.tenant import Tenant, TenantMember
from app.utils.exceptions import NotFoundError


class TestTenantContextHelpers:
    def test_multi_tenant_flag(self) -> None:
        with patch("app.core.tenant_context.settings") as s:
            s.MULTI_TENANT_ENABLED = False
            assert multi_tenant_enabled() is False
            s.MULTI_TENANT_ENABLED = True
            assert multi_tenant_enabled() is True

    def test_ensure_tenant_resource_blocks_cross(self) -> None:
        with patch("app.core.tenant_context.multi_tenant_enabled", return_value=True):
            set_tenant_context(
                TenantContext(
                    tenant_id="ten-a",
                    tenant_slug="a",
                    member_role="member",
                    enforced=True,
                )
            )
            ensure_tenant_resource("ten-a", resource="Task", resource_id="1")
            with pytest.raises(NotFoundError):
                ensure_tenant_resource("ten-b", resource="Task", resource_id="2")
            with pytest.raises(NotFoundError):
                ensure_tenant_resource(None, resource="Task", resource_id="3")
            set_tenant_context(None)

    def test_apply_tenant_filter_sql(self) -> None:
        with patch("app.core.tenant_context.multi_tenant_enabled", return_value=True):
            set_tenant_context(
                TenantContext(
                    tenant_id="ten-a",
                    tenant_slug="a",
                    member_role="member",
                    enforced=True,
                )
            )
            q = apply_tenant_filter(select(Task), Task)
            compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
            assert "tenant_id" in compiled.lower() or "ten-a" in compiled
            set_tenant_context(None)


class TestCrossTenantAccess:
    def test_tenant_a_cannot_access_tenant_b_task(self) -> None:
        task_b = Task(
            name="b-task",
            description="",
            agent_config={},
            status=TaskStatus.CREATED,
            created_by="bob",
            tenant_id="tenant-b",
        )
        task_b.id = "task-b-1"

        with patch("app.core.tenant_context.multi_tenant_enabled", return_value=True):
            # Alice in tenant A
            set_tenant_context(
                TenantContext(
                    tenant_id="tenant-a",
                    tenant_slug="a",
                    member_role="member",
                    enforced=True,
                )
            )
            with patch("app.core.tenancy.settings") as s:
                s.AUTH_ENABLED = True
                s.TENANCY_ENABLED = True
                s.ADMIN_ACTORS = "admin"
                assert can_access_task(task_b, "alice") is False
                assert can_access_task(task_b, "bob") is False  # wrong tenant

            # Bob in tenant B owns the task
            set_tenant_context(
                TenantContext(
                    tenant_id="tenant-b",
                    tenant_slug="b",
                    member_role="member",
                    enforced=True,
                )
            )
            with patch("app.core.tenancy.settings") as s:
                s.AUTH_ENABLED = True
                s.TENANCY_ENABLED = True
                s.ADMIN_ACTORS = "admin"
                assert can_access_task(task_b, "bob") is True
                assert can_access_task(task_b, "alice") is False

            set_tenant_context(None)

    def test_same_tenant_owner_isolation_still_applies(self) -> None:
        task = Task(
            name="t",
            description="",
            agent_config={},
            created_by="alice",
            tenant_id="tenant-a",
        )
        with patch("app.core.tenant_context.multi_tenant_enabled", return_value=True):
            set_tenant_context(
                TenantContext(
                    tenant_id="tenant-a",
                    tenant_slug="a",
                    member_role="member",
                    enforced=True,
                )
            )
            with patch("app.core.tenancy.settings") as s:
                s.AUTH_ENABLED = True
                s.TENANCY_ENABLED = True
                s.ADMIN_ACTORS = "admin"
                assert can_access_task(task, "alice") is True
                assert can_access_task(task, "bob") is False
            set_tenant_context(None)


class TestTenantModels:
    def test_tenant_member_repr(self) -> None:
        t = Tenant(id=str(uuid4()), name="Acme", slug="acme", status="active")
        m = TenantMember(
            id=str(uuid4()),
            tenant_id=t.id,
            user_id="alice",
            role="tenant_admin",
        )
        assert "acme" in repr(t)
        assert "alice" in repr(m)
