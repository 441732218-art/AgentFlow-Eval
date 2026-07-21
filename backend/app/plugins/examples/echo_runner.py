# (c) 2026 AgentFlow-Eval
"""Example AGENT_RUNNER plugin — deterministic echo runner."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.agent_runner.base import AgentResult, BaseAgentRunner
from app.core.plugins.base import BasePlugin, PluginContext, PluginMeta, PluginType


class EchoAgentRunner(BaseAgentRunner):
    """Returns the user query as a single final answer step (no LLM)."""

    async def run(
        self,
        query: str,
        tools: list[Any] | None = None,
        *,
        agent_config: dict[str, Any] | None = None,
    ) -> AgentResult:
        _ = tools
        cfg = dict(agent_config or {})
        prefix = str(cfg.get("prefix") or "ECHO: ")
        text = f"{prefix}{query}"
        steps = [
            {
                "type": "thought",
                "content": "Echo runner reflects the query without external calls.",
            },
            {
                "type": "final",
                "content": text,
                "answer": text,
            },
        ]
        return AgentResult(
            steps=steps,
            total_tokens=0,
            response_time_ms=1,
            status="success",
            final_answer=text,
            runner="echo",
            finished_at=datetime.now(timezone.utc),
        )


class Plugin(BasePlugin):
    meta = PluginMeta(
        name="echo_runner",
        version="1.0.0",
        plugin_type=PluginType.AGENT_RUNNER,
        description="Deterministic echo AgentRunner (example).",
        author="AgentFlow-Eval",
        provides=["echo", "echo_runner"],
    )

    def on_activate(self, ctx: PluginContext) -> None:
        assert ctx.register_runner is not None

        def factory(agent_config: dict[str, Any]) -> EchoAgentRunner:
            return EchoAgentRunner()

        ctx.register_runner("echo", factory)
        ctx.register_runner("echo_runner", factory)
