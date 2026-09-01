# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool capability definitions for Runtime integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALLOWED_EXECUTOR_TYPES = frozenset({"local", "remote", "future_provider"})


@dataclass
class ToolDefinition:
    """Capability metadata for a tool (not an executable implementation)."""

    name: str
    description: str
    executor_type: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_tool_definition(definition: ToolDefinition) -> None:
    """Validate a tool definition before registration."""
    name = (definition.name or "").strip()
    if not name:
        raise ValueError("ToolDefinition.name must be a non-empty string")
    description = (definition.description or "").strip()
    if not description:
        raise ValueError("ToolDefinition.description must be a non-empty string")
    executor_type = (definition.executor_type or "").strip()
    if executor_type not in ALLOWED_EXECUTOR_TYPES:
        allowed = ", ".join(sorted(ALLOWED_EXECUTOR_TYPES))
        raise ValueError(
            f"ToolDefinition.executor_type must be one of: {allowed}"
        )
    if not isinstance(definition.input_schema, dict):
        raise ValueError("ToolDefinition.input_schema must be a dict")
    if not isinstance(definition.metadata, dict):
        raise ValueError("ToolDefinition.metadata must be a dict")
