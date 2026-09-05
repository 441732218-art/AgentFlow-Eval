# AgentFlow Intelligence v2.0 — Trade Application Tool Provider
"""Example agent configurations for the trade application provider."""

from __future__ import annotations

from app.runtime.agent.models import AgentDefinition

TRADE_SALES_AGENT = AgentDefinition(
    id="trade.sales_agent",
    name="Trade Sales Agent",
    tool_names=["trade.search_customer"],
    roles=("sales",),
)

TRADE_SUPPORT_AGENT = AgentDefinition(
    id="trade.support_agent",
    name="Trade Support Agent",
    tool_names=["trade.search_customer"],
    roles=("support",),
)
