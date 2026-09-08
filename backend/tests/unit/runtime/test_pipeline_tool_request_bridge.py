# AgentFlow Intelligence v2.0 — Pipeline structured tool request bridge (Phase V2.1.7)

from __future__ import annotations

import pytest

from app.applications.trade_provider.agents import TRADE_SALES_AGENT
from app.applications.trade_provider.tools import TOOL_DEFINITIONS
from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.executor.context_fields import TOOL_REQUEST_METADATA_KEY
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.policy.role_based_engine import RoleBasedPolicyEngine
from app.runtime.service.tooling_bootstrap import bootstrap_production_tooling, reset_production_tooling
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.registry import get_local_handler_registry


def _trade_search_customer_capability() -> ToolCapability:
    definition = next(d for d in TOOL_DEFINITIONS if d.name == "trade.search_customer")
    scope = tuple(definition.metadata.get("permission_scope", ()))
    return ToolCapability(
        tool_name=definition.name,
        description=definition.description,
        permission_scope=scope,
        metadata=dict(definition.metadata),
    )


def _trade_agent_runtime() -> AgentRuntime:
    bootstrap_production_tooling()
    production_runtime = create_production_runtime()
    engine = create_tool_execution_engine(handler_registry=get_local_handler_registry())
    production_runtime.tool_execution_engine = engine

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(_trade_search_customer_capability())
    permission_evaluator = PermissionEvaluator(RoleBasedPolicyEngine())
    agent_runtime = AgentRuntime(
        production_runtime,
        tool_registry=tool_registry,
        permission_evaluator=permission_evaluator,
    )
    agent_runtime._agent_pipeline._execution_pipeline.tool_execution_engine = engine
    return agent_runtime


@pytest.fixture(autouse=True)
def _reset_tooling_state() -> None:
    reset_production_tooling()
    yield
    reset_production_tooling()


def test_agent_runtime_executes_structured_tool_request() -> None:
    agent_runtime = _trade_agent_runtime()
    context = create_execution_context(
        agent_runtime._production_runtime,
        execution_id="exec-tool-bridge-1",
        agent_id=TRADE_SALES_AGENT.id,
    )
    context.metadata[TOOL_REQUEST_METADATA_KEY] = {
        "tool": "trade.search_customer",
        "arguments": {
            "product": "wood furniture",
            "country": "Germany",
        },
    }

    result = agent_runtime.execute(
        TRADE_SALES_AGENT,
        "Find German furniture buyers",
        context,
    )

    assert result.error is None
    assert result.session.status == "COMPLETED"
    assert isinstance(result.output, list)
    assert len(result.output) >= 1
    assert result.output[0]["country"] == "Germany"
    assert "match_reason" in result.output[0]
    assert result.output[0]["company"] == "ABC Furniture GmbH"


def test_structured_tool_request_denied_when_tool_not_in_agent_tool_names() -> None:
    agent_runtime = _trade_agent_runtime()
    agent = AgentDefinition(
        id="agent-no-tools",
        name="Agent Without Tools",
        tool_names=[],
    )
    context = create_execution_context(
        agent_runtime._production_runtime,
        execution_id="exec-tool-bridge-2",
        agent_id=agent.id,
    )
    context.metadata[TOOL_REQUEST_METADATA_KEY] = {
        "tool": "trade.search_customer",
        "arguments": {"product": "wood furniture", "country": "Germany"},
    }

    result = agent_runtime.execute(agent, "Find German furniture buyers", context)

    assert result.session.status == "FAILED"
    assert result.error is not None
    assert "trade.search_customer" in result.error


def test_structured_tool_request_denied_when_security_dependencies_missing() -> None:
    bootstrap_production_tooling()
    production_runtime = create_production_runtime()
    engine = create_tool_execution_engine(handler_registry=get_local_handler_registry())
    production_runtime.tool_execution_engine = engine

    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-tool-bridge-missing-deps",
        agent_id=TRADE_SALES_AGENT.id,
    )
    context.metadata[TOOL_REQUEST_METADATA_KEY] = {
        "tool": "trade.search_customer",
        "arguments": {
            "product": "wood furniture",
            "country": "Germany",
        },
    }

    result = pipeline.run(TRADE_SALES_AGENT, "Find German furniture buyers", context)

    assert result.status == "FAILED"
    error_message = result.metadata.get("error_message")
    assert error_message is not None
    assert "安全依赖未配置，拒绝执行" in error_message
    assert result.output is None


def test_plain_string_task_without_tool_request_unchanged() -> None:
    agent_runtime = _trade_agent_runtime()
    context = create_execution_context(
        agent_runtime._production_runtime,
        execution_id="exec-tool-bridge-3",
        agent_id=TRADE_SALES_AGENT.id,
    )

    result = agent_runtime.execute(TRADE_SALES_AGENT, "hello", context)

    assert result.error is None
    assert result.output == "pipeline execution completed"
