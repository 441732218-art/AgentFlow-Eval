# (c) 2026 AgentFlow-Eval
"""Example HOOK plugin — records pre/post pipeline events in-memory."""

from __future__ import annotations

from typing import Any

from app.core.plugins.base import (
    HOOK_POST_AGENT_RUN,
    HOOK_POST_JUDGE,
    HOOK_PRE_AGENT_RUN,
    HOOK_PRE_JUDGE,
    BasePlugin,
    PluginContext,
    PluginMeta,
    PluginType,
)

# Module-level ring buffer for tests / debugging
_EVENT_LOG: list[dict[str, Any]] = []
_MAX = 200


def get_event_log() -> list[dict[str, Any]]:
    return list(_EVENT_LOG)


def clear_event_log() -> None:
    _EVENT_LOG.clear()


def _append(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = {"event": event, **{k: v for k, v in payload.items() if k != "event"}}
    _EVENT_LOG.append(item)
    if len(_EVENT_LOG) > _MAX:
        del _EVENT_LOG[: len(_EVENT_LOG) - _MAX]
    return item


class Plugin(BasePlugin):
    meta = PluginMeta(
        name="audit_hooks",
        version="1.0.0",
        plugin_type=PluginType.HOOK,
        description="Logs pre/post agent and judge hooks (example).",
        author="AgentFlow-Eval",
        provides=[],
    )

    def on_activate(self, ctx: PluginContext) -> None:
        assert ctx.register_hook is not None

        def pre_agent(payload: dict[str, Any]) -> dict[str, Any]:
            return _append(HOOK_PRE_AGENT_RUN, payload)

        def post_agent(payload: dict[str, Any]) -> dict[str, Any]:
            return _append(HOOK_POST_AGENT_RUN, payload)

        def pre_judge(payload: dict[str, Any]) -> dict[str, Any]:
            return _append(HOOK_PRE_JUDGE, payload)

        def post_judge(payload: dict[str, Any]) -> dict[str, Any]:
            return _append(HOOK_POST_JUDGE, payload)

        ctx.register_hook(HOOK_PRE_AGENT_RUN, pre_agent, priority=50)
        ctx.register_hook(HOOK_POST_AGENT_RUN, post_agent, priority=50)
        ctx.register_hook(HOOK_PRE_JUDGE, pre_judge, priority=50)
        ctx.register_hook(HOOK_POST_JUDGE, post_judge, priority=50)
