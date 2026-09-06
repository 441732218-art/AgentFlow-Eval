# AgentFlow Intelligence v2.0 — Trade search_customer handler tests (Phase V2.1.6)

from __future__ import annotations

from app.applications.bootstrap import bootstrap_applications
from app.applications.trade_provider.handlers import search_customer
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import attach_tool_request
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import create_tool_registry


def test_search_customer_matches_product_and_country() -> None:
    results = search_customer(product="wood furniture", country="Germany")

    assert len(results) >= 1
    assert all(item["country"] == "Germany" for item in results)
    assert all("match_reason" in item for item in results)
    companies = {item["company"] for item in results}
    assert "ABC Furniture GmbH" in companies


def test_search_customer_returns_empty_for_unknown_product() -> None:
    results = search_customer(product="nonexistent product xyz")

    assert results == []


def test_search_customer_executes_via_manual_tool_request() -> None:
    """Tool + handler path verified via explicit attach_tool_request.

    NOTE: AgentRuntime does not yet auto-invoke ``AgentDefinition.tool_names``
    during pipeline execution. Automatic "agent task -> tool call" wiring is
    a separate follow-up; this test only proves the local handler returns real
    customer data when the pipeline is given an explicit tool request.
    """
    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)
    engine = create_tool_execution_engine(handler_registry=handlers)
    pipeline = ExecutionPipeline(tool_execution_engine=engine)

    definition = registry.get("trade.search_customer")
    runtime = create_production_runtime()
    execution_context = create_execution_context(
        runtime,
        execution_id="exec-trade-search-1",
        agent_id="trade.sales_agent",
    )
    context = RuntimeContext(
        execution_id=execution_context.execution_id,
        agent_id=execution_context.agent_id,
    )
    attach_tool_request(
        context,
        definition,
        {"product": "wood furniture", "country": "Germany"},
    )

    output = pipeline.run(context, "Find German furniture buyers")

    assert isinstance(output, list)
    assert len(output) >= 1
    assert output[0]["country"] == "Germany"
    assert "match_reason" in output[0]
    assert output[0]["company"] == "ABC Furniture GmbH"
