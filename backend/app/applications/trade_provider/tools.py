# AgentFlow Intelligence v2.0 — Trade Application Tool Provider
"""Tool definitions for the trade application provider template."""

from __future__ import annotations

from app.runtime.tools.definition import ToolDefinition

TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="trade.search_customer",
        description="Search potential customers for trade business",
        executor_type="remote",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "country": {"type": "string"},
            },
        },
        metadata={
            "provider": "trade",
            "category": "customer",
        },
    ),
    ToolDefinition(
        name="trade.generate_email",
        description="Generate outbound sales email draft",
        executor_type="local",
        input_schema={
            "type": "object",
            "properties": {
                "customer": {"type": "string"},
                "product": {"type": "string"},
                "language": {"type": "string"},
            },
        },
        metadata={
            "provider": "trade",
            "category": "email",
        },
    ),
    ToolDefinition(
        name="trade.create_followup",
        description="Create customer followup task",
        executor_type="remote",
        input_schema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "stage": {"type": "string"},
            },
        },
        metadata={
            "provider": "trade",
            "category": "followup",
        },
    ),
]
