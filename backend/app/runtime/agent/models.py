# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent definition model for runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    """Runtime agent definition without application-layer coupling."""

    id: str
    name: str
    tool_names: list[str]
    version: str = "1.0"
    enabled: bool = True
    roles: tuple[str, ...] = ()
    description: str = ""
    system_prompt: str = ""
    model_config: dict[str, Any] = field(default_factory=dict)
    memory_config: dict[str, Any] = field(default_factory=dict)
    evaluation_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tools(self) -> list[str]:
        """Alias for ``tool_names`` (commercial agent API)."""
        return self.tool_names
