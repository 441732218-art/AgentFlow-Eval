# AgentFlow Intelligence v2.0 — RoleBasedPolicyEngine tests

from __future__ import annotations

import pytest

from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.policy.role_based_engine import RoleBasedPolicyEngine
from app.runtime.tool_registry.models import ToolCapability
from app.runtime.tools.definition import ToolDefinition


def _context(*, role: str) -> ExecutionContext:
    production_runtime = create_production_runtime()
    return create_execution_context(
        production_runtime,
        execution_id=f"exec-role-{role}",
        agent_id=f"agent-{role}",
        user_id=f"user-{role}",
        metadata={"role": role, "roles": [role]},
    )


def _tool_with_scope(permission_scope: tuple[str, ...]) -> ToolDefinition:
    return ToolDefinition(
        name="trade.search_customer",
        description="Search customers",
        executor_type="remote",
        metadata={"permission_scope": list(permission_scope)},
    )


def _capability_with_scope(permission_scope: tuple[str, ...]) -> ToolCapability:
    return ToolCapability(
        tool_name="trade.search_customer",
        description="Search customers",
        permission_scope=permission_scope,
    )


def test_sales_role_allowed_for_sales_scoped_tool() -> None:
    engine = RoleBasedPolicyEngine()
    decision = engine.evaluate(
        _context(role="sales"),
        _tool_with_scope(("sales",)),
    )

    assert decision.allowed is True
    assert decision.policy_name == "role_based"


def test_support_role_denied_for_sales_scoped_tool() -> None:
    engine = RoleBasedPolicyEngine()
    decision = engine.evaluate(
        _context(role="support"),
        _tool_with_scope(("sales",)),
    )

    assert decision.allowed is False
    assert "Role not permitted" in (decision.reason or "")
    assert decision.metadata["permission_scope"] == ["sales"]
    assert decision.metadata["caller_roles"] == ["support"]


def test_empty_permission_scope_allows_any_role() -> None:
    engine = RoleBasedPolicyEngine()

    for role in ("sales", "support", "admin"):
        decision = engine.evaluate(_context(role=role), _tool_with_scope(()))
        assert decision.allowed is True


def test_blocked_tools_denies_even_when_role_matches() -> None:
    engine = RoleBasedPolicyEngine(blocked_tools=["trade.search_customer"])
    decision = engine.evaluate(
        _context(role="sales"),
        _tool_with_scope(("sales",)),
    )

    assert decision.allowed is False
    assert "blocked" in (decision.reason or "").lower()


def test_permission_evaluator_with_role_based_engine_denies_support() -> None:
    evaluator = PermissionEvaluator(RoleBasedPolicyEngine())
    capability = _capability_with_scope(("sales",))

    decision = evaluator.evaluate_tool_access(_context(role="support"), capability)

    assert decision.allowed is False
