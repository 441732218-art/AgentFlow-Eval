# AgentFlow Intelligence v2.0 — Trade Application Tool Provider
"""Registration logic for the trade application provider."""

from __future__ import annotations

from app.applications.provider import ApplicationToolProvider
from app.applications.trade_provider.handlers import trade_generate_email_handler
from app.applications.trade_provider.tools import TOOL_DEFINITIONS
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import ToolRegistry


class TradeApplicationProvider(ApplicationToolProvider):
    """Trade business application registering ``trade.*`` tool capabilities."""

    def register_tools(
        self,
        registry: ToolRegistry,
        handler_registry: LocalHandlerRegistry,
    ) -> None:
        for definition in TOOL_DEFINITIONS:
            registry.register(definition)
        handler_registry.register("trade.generate_email", trade_generate_email_handler)
