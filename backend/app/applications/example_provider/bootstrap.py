# AgentFlow Intelligence v2.0 — Example Application Tool Provider
"""Registration logic for the example application provider."""

from __future__ import annotations

from app.applications.example_provider.handlers import app_example_echo_handler
from app.applications.example_provider.tools import TOOL_DEFINITIONS
from app.applications.provider import ApplicationToolProvider
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import ToolRegistry


class ExampleApplicationToolProvider(ApplicationToolProvider):
    """Example application registering ``app_example.*`` tools."""

    def register_tools(
        self,
        registry: ToolRegistry,
        handler_registry: LocalHandlerRegistry,
    ) -> None:
        for definition in TOOL_DEFINITIONS:
            registry.register(definition)
        handler_registry.register("app_example.echo", app_example_echo_handler)
