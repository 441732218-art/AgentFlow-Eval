# EXPERIMENTAL — Registry bridge feasibility probe (audit-only; safe to delete)
"""Probe ToolDefinition -> ToolCapability bridging for Path 3 permission precheck.

This file does NOT modify production code. It validates whether a manually
bridged trade.search_customer capability can flow through tool_registry and
PermissionEvaluator. Role-based allow/deny behaviour is reported honestly
against the current InMemoryPolicyEngine implementation.
"""

from __future__ import annotations

import pytest

from app.applications.trade_provider.tools import TOOL_DEFINITIONS
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.policy.role_based_engine import RoleBasedPolicyEngine
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability
from app.runtime.tool_registry.registry import resolve_tool_capability
from app.runtime.tools.definition import ToolDefinition


def _trade_search_customer_definition() -> ToolDefinition:
    by_name = {definition.name: definition for definition in TOOL_DEFINITIONS}
    return by_name["trade.search_customer"]


def _bridge_tool_definition_to_capability(
    definition: ToolDefinition,
    *,
    permission_scope: tuple[str, ...],
    version: str = "1.0",
    capability_tags: tuple[str, ...] = (),
    enabled: bool = True,
) -> ToolCapability:
    """Manual bridge — maps shared fields and injects capability-only data."""
    merged_metadata = {
        **dict(definition.metadata),
        "executor_type": definition.executor_type,
        "input_schema": dict(definition.input_schema),
    }
    tags = capability_tags or tuple(
        value
        for value in (definition.metadata.get("provider"), definition.metadata.get("category"))
        if value
    )
    return ToolCapability(
        tool_name=definition.name,
        version=version,
        description=definition.description,
        capability_tags=tags,
        permission_scope=permission_scope,
        enabled=enabled,
        metadata=merged_metadata,
    )


def _sales_agent_context(*, role: str) -> ExecutionContext:
    production_runtime = create_production_runtime()
    return create_execution_context(
        production_runtime,
        execution_id=f"exec-bridge-{role}",
        agent_id=f"agent-{role}",
        user_id=f"user-{role}",
        metadata={"role": role, "roles": [role]},
    )


@pytest.fixture
def bridged_trade_search_registry() -> InMemoryToolRegistry:
    definition = _trade_search_customer_definition()
    capability = _bridge_tool_definition_to_capability(
        definition,
        permission_scope=("sales",),
    )
    registry = InMemoryToolRegistry()
    registry.register(capability)
    return registry


def test_experimental_bridge_maps_tool_definition_fields() -> None:
    definition = _trade_search_customer_definition()
    capability = _bridge_tool_definition_to_capability(
        definition,
        permission_scope=("sales",),
    )

    assert capability.tool_name == definition.name == "trade.search_customer"
    assert capability.description == definition.description
    assert capability.metadata["executor_type"] == "local"
    assert capability.metadata["provider"] == "trade"
    assert capability.metadata["category"] == "customer"
    assert capability.metadata["input_schema"] == definition.input_schema
    assert capability.permission_scope == ("sales",)
    assert capability.capability_tags == ("trade", "customer")


def test_experimental_register_and_resolve_capability(
    bridged_trade_search_registry: InMemoryToolRegistry,
) -> None:
    capability = resolve_tool_capability(
        bridged_trade_search_registry,
        "trade.search_customer",
    )

    assert capability.tool_name == "trade.search_customer"
    assert capability.permission_scope == ("sales",)


def test_experimental_sales_role_evaluator_returns_allow(
    bridged_trade_search_registry: InMemoryToolRegistry,
) -> None:
    capability = resolve_tool_capability(
        bridged_trade_search_registry,
        "trade.search_customer",
    )
    evaluator = PermissionEvaluator(InMemoryPolicyEngine())
    context = _sales_agent_context(role="sales")

    decision = evaluator.evaluate_tool_access(context, capability)

    assert decision.allowed is True


def test_experimental_non_sales_role_denied_with_role_based_engine(
    bridged_trade_search_registry: InMemoryToolRegistry,
) -> None:
    capability = resolve_tool_capability(
        bridged_trade_search_registry,
        "trade.search_customer",
    )
    evaluator = PermissionEvaluator(RoleBasedPolicyEngine())
    context = _sales_agent_context(role="support")

    decision = evaluator.evaluate_tool_access(context, capability)

    assert decision.allowed is False
    assert "Role not permitted" in (decision.reason or "")


def test_experimental_blocked_tool_path_returns_deny(
    bridged_trade_search_registry: InMemoryToolRegistry,
) -> None:
    """Shows deny mechanism that exists today (blocked_tools), not role matching."""
    capability = resolve_tool_capability(
        bridged_trade_search_registry,
        "trade.search_customer",
    )
    evaluator = PermissionEvaluator(
        InMemoryPolicyEngine(blocked_tools=["trade.search_customer"]),
    )
    context = _sales_agent_context(role="sales")

    decision = evaluator.evaluate_tool_access(context, capability)

    assert decision.allowed is False
    assert "blocked" in (decision.reason or "").lower()
