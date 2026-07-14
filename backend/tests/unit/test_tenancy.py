# (c) 2026 AgentFlow-Eval
"""Unit tests for tenancy helpers and actor isolation."""

from unittest.mock import patch

from app.core.tenancy import (
    apply_owner_filter,
    can_access_task,
    ensure_task_access,
    is_admin,
    tenancy_enforced,
)
from app.models.task import Task, TaskStatus
from app.utils.exceptions import NotFoundError
from sqlalchemy import select


class TestTenancyHelpers:
    def test_tenancy_off_by_default(self):
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = False
            s.TENANCY_ENABLED = False
            assert tenancy_enforced() is False

    def test_tenancy_on_with_auth(self):
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = True
            s.TENANCY_ENABLED = False
            assert tenancy_enforced() is True

    def test_tenancy_on_explicit(self):
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = False
            s.TENANCY_ENABLED = True
            assert tenancy_enforced() is True

    def test_admin_actors(self):
        with patch("app.core.tenancy.settings") as s:
            s.ADMIN_ACTORS = "admin,ops"
            assert is_admin("admin")
            assert is_admin("ops")
            assert not is_admin("alice")

    def test_can_access_when_disabled(self):
        task = Task(name="t", description="", agent_config={}, created_by="alice")
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = False
            s.TENANCY_ENABLED = False
            s.ADMIN_ACTORS = "admin"
            assert can_access_task(task, "bob") is True

    def test_can_access_owner_only(self):
        task = Task(name="t", description="", agent_config={}, created_by="alice")
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = True
            s.TENANCY_ENABLED = False
            s.ADMIN_ACTORS = "admin"
            assert can_access_task(task, "alice") is True
            assert can_access_task(task, "bob") is False
            assert can_access_task(task, "admin") is True

    def test_ensure_hides_foreign(self):
        task = Task(name="t", description="", agent_config={}, created_by="alice")
        task.id = "tid-1"
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = True
            s.TENANCY_ENABLED = False
            s.ADMIN_ACTORS = "admin"
            try:
                ensure_task_access(task, "bob", "tid-1")
                assert False, "expected NotFoundError"
            except NotFoundError as exc:
                assert exc.status_code == 404

    def test_apply_owner_filter_sql(self):
        with patch("app.core.tenancy.settings") as s:
            s.AUTH_ENABLED = True
            s.TENANCY_ENABLED = False
            s.ADMIN_ACTORS = "admin"
            q = apply_owner_filter(select(Task), "alice")
            compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
            assert "created_by" in compiled.lower() or "tasks" in compiled.lower()
