# AgentFlow Intelligence v2.0 — Application Tool Provider Layer
"""Contract for external application systems registering tools with Runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import ToolRegistry


class ApplicationToolProvider(ABC):
    """Register application-owned tool capabilities into Runtime registries.

    Implementations live under ``backend/app/applications/<name>_provider/``.
    Runtime Core must never import those modules directly.
    """

    @abstractmethod
    def register_tools(
        self,
        registry: ToolRegistry,
        handler_registry: LocalHandlerRegistry,
    ) -> None:
        """Register tool definitions and local handlers into the given registries."""
