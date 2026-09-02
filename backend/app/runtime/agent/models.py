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
    metadata: dict[str, Any] = field(default_factory=dict)
