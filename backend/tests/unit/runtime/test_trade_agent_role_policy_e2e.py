# AgentFlow Intelligence v2.0 — Trade agent role policy E2E (Path 3 probe)

from __future__ import annotations

import pytest

from app.applications.trade_provider.agents import TRADE_SALES_AGENT, TRADE_SUPPORT_AGENT
from app.applications.trade_provider.tools import TOOL_DEFINITIONS
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.policy.models import PolicyDeniedError
from app.runtime.policy.role_based_engine import RoleBasedPolicyEngine
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability


def _trade_search_customer_capability() -> ToolCapability:
    definition = next(d for d in TOOL_DEFINITIONS if d.name == "trade.search_customer")
    scope = tuple(definition.metadata.get("permission_scope", ()))
    return ToolCapability(
        tool_name=definition.name,
        description=definition.description,
        permission_scope=scope,
        metadata=dict(definition.metadata),
    )


def _path3_runtime() -> AgentRuntime:
    production_runtime = create_production_runtime()
    tool_registry = InMemoryToolRegistry()
    tool_registry.register(_trade_search_customer_capability())
    permission_evaluator = PermissionEvaluator(RoleBasedPolicyEngine())
    return AgentRuntime(
        production_runtime,
        tool_registry=tool_registry,
        permission_evaluator=permission_evaluator,
    )


def test_sales_agent_allowed_for_trade_search_customer_via_path3() -> None:
    runtime = _path3_runtime()

    result = runtime.execute(TRADE_SALES_AGENT, "search customers in US")

    assert result.error is None
    assert result.session.status == "COMPLETED"


def test_support_agent_denied_for_trade_search_customer_via_path3() -> None:
    runtime = _path3_runtime()

    with pytest.raises(PolicyDeniedError, match="trade.search_customer"):
        runtime.execute(TRADE_SUPPORT_AGENT, "search customers in US")
