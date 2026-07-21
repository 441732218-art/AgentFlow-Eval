# (c) 2026 AgentFlow-Eval
"""Capability registry for plugin-provided runners, judges, and tools."""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.core.plugins.base import AgentRunnerFactory, JudgeFactory, ToolSpec

logger = logging.getLogger(__name__)


class PluginCapabilityRegistry:
    """Maps capability keys → factories contributed by plugins."""

    def __init__(self) -> None:
        self._runners: dict[str, tuple[str, AgentRunnerFactory]] = {}
        self._judges: dict[str, tuple[str, JudgeFactory]] = {}
        self._tools: dict[str, ToolSpec] = {}

    # ---- runners ----
    def register_runner(
        self,
        key: str,
        factory: Callable[[dict[str, Any]], Any] | AgentRunnerFactory,
        *,
        plugin_id: str,
    ) -> None:
        key = str(key).lower().strip()
        if not key:
            raise ValueError("runner key required")
        if not isinstance(factory, AgentRunnerFactory):
            factory = AgentRunnerFactory(factory)
        if key in self._runners and self._runners[key][0] != plugin_id:
            logger.warning(
                "Runner key %r overridden by plugin %s (was %s)",
                key,
                plugin_id,
                self._runners[key][0],
            )
        self._runners[key] = (plugin_id, factory)
        logger.info("Registered plugin runner %r from %s", key, plugin_id)

    def unregister_runners(self, plugin_id: str) -> int:
        keys = [k for k, (pid, _) in self._runners.items() if pid == plugin_id]
        for k in keys:
            del self._runners[k]
        return len(keys)

    def get_runner_factory(self, key: str) -> AgentRunnerFactory | None:
        item = self._runners.get(str(key).lower().strip())
        return item[1] if item else None

    def list_runners(self) -> list[dict[str, Any]]:
        return [
            {"key": k, "plugin_id": pid}
            for k, (pid, _) in sorted(self._runners.items())
        ]

    # ---- judges ----
    def register_judge(
        self,
        key: str,
        factory: Callable[[], Any] | JudgeFactory,
        *,
        plugin_id: str,
    ) -> None:
        key = str(key).lower().strip()
        if not key:
            raise ValueError("judge key required")
        if not isinstance(factory, JudgeFactory):
            factory = JudgeFactory(factory)
        self._judges[key] = (plugin_id, factory)
        logger.info("Registered plugin judge %r from %s", key, plugin_id)

    def unregister_judges(self, plugin_id: str) -> int:
        keys = [k for k, (pid, _) in self._judges.items() if pid == plugin_id]
        for k in keys:
            del self._judges[k]
        return len(keys)

    def get_judge_factory(self, key: str) -> JudgeFactory | None:
        item = self._judges.get(str(key).lower().strip())
        return item[1] if item else None

    def list_judges(self) -> list[dict[str, Any]]:
        return [
            {"key": k, "plugin_id": pid} for k, (pid, _) in sorted(self._judges.items())
        ]

    # ---- tools ----
    def register_tool(self, spec: ToolSpec, *, plugin_id: str) -> None:
        if not spec.name:
            raise ValueError("tool name required")
        if not callable(spec.fn):
            raise ValueError(f"tool {spec.name!r} requires callable fn")
        spec.source_plugin = plugin_id
        self._tools[spec.name] = spec
        logger.info("Registered plugin tool %r from %s", spec.name, plugin_id)

    def unregister_tools(self, plugin_id: str) -> int:
        keys = [k for k, s in self._tools.items() if s.source_plugin == plugin_id]
        for k in keys:
            del self._tools[k]
        return len(keys)

    def get_tool(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def get_tool_fn(self, name: str) -> Callable[..., str] | None:
        spec = self._tools.get(name)
        return spec.fn if spec else None

    def list_tools(self) -> list[dict[str, Any]]:
        out = []
        for name, spec in sorted(self._tools.items()):
            out.append(
                {
                    "name": name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                    "required": list(spec.required),
                    "network": spec.network,
                    "plugin_id": spec.source_plugin,
                }
            )
        return out

    def clear(self) -> None:
        self._runners.clear()
        self._judges.clear()
        self._tools.clear()


_default_caps: PluginCapabilityRegistry | None = None


def get_capability_registry() -> PluginCapabilityRegistry:
    global _default_caps
    if _default_caps is None:
        _default_caps = PluginCapabilityRegistry()
    return _default_caps


def reset_capability_registry() -> PluginCapabilityRegistry:
    global _default_caps
    _default_caps = PluginCapabilityRegistry()
    return _default_caps
