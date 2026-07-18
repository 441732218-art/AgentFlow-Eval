# (c) 2026 AgentFlow-Eval
"""Example TOOL plugin — echo arguments as JSON."""

from __future__ import annotations

import json
from typing import Any

from app.core.plugins.base import BasePlugin, PluginContext, PluginMeta, PluginType


def _echo_tool(**kwargs: Any) -> str:
    return json.dumps({"echo": kwargs}, ensure_ascii=False)


class Plugin(BasePlugin):
    meta = PluginMeta(
        name="echo_tool",
        version="1.0.0",
        plugin_type=PluginType.TOOL,
        description="Echo tool arguments as JSON (example).",
        author="AgentFlow-Eval",
        provides=["echo"],
    )

    def on_activate(self, ctx: PluginContext) -> None:
        assert ctx.register_tool is not None
        ctx.register_tool(
            "echo",
            _echo_tool,
            description="Echo back all tool arguments as a JSON object.",
            parameters={
                "message": {
                    "type": "string",
                    "description": "Optional message to echo",
                },
            },
            required=[],
            network=False,
        )
