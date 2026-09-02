# AgentFlow Intelligence v2.0 — Example Application Tool Provider
"""Tool definitions owned by the example application provider."""

from __future__ import annotations

from app.runtime.tools.definition import ToolDefinition

APP_EXAMPLE_REMOTE_ENDPOINT = "http://mock.test/applications/invoke"

TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="app_example.echo",
        description="Application-layer example echo tool",
        executor_type="local",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
        metadata={"application": "example_provider", "example": True},
    ),
    ToolDefinition(
        name="app_example.remote_search",
        description="Application-layer example remote search tool",
        executor_type="remote",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        metadata={
            "application": "example_provider",
            "example": True,
            "endpoint": APP_EXAMPLE_REMOTE_ENDPOINT,
            "provider_id": "app-example-mock-provider",
            "version": "1",
        },
    ),
]
