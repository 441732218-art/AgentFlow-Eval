# AgentFlow Intelligence v2.0 — Application Tool Provider Layer
"""Orchestrate application provider registration into Runtime registries."""

from __future__ import annotations

from app.applications.example_provider import ExampleApplicationToolProvider
from app.applications.provider import ApplicationToolProvider
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import ToolRegistry

DEFAULT_APPLICATION_PROVIDERS: list[ApplicationToolProvider] = [
    ExampleApplicationToolProvider(),
]


def bootstrap_applications(
    registry: ToolRegistry,
    handler_registry: LocalHandlerRegistry,
) -> None:
    """Register tools from all configured application providers.

    Callers must pass explicit registry instances. This function does not
    mutate module-level singletons. Production wiring invokes it once via
    ``runtime.service.tooling_bootstrap.bootstrap_production_tooling()``.
    """
    for provider in DEFAULT_APPLICATION_PROVIDERS:
        provider.register_tools(registry, handler_registry)
