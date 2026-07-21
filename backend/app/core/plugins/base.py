# (c) 2026 AgentFlow-Eval
"""Plugin contracts: types, metadata, lifecycle base class."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class PluginType(str, Enum):
    """Supported extension kinds."""

    AGENT_RUNNER = "agent_runner"
    JUDGE = "judge"
    TOOL = "tool"
    HOOK = "hook"


class PluginState(str, Enum):
    """Plugin lifecycle states."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    UNLOADED = "unloaded"


# Well-known hook names (pre/post around core pipelines)
HOOK_PRE_AGENT_RUN = "pre_agent_run"
HOOK_POST_AGENT_RUN = "post_agent_run"
HOOK_PRE_JUDGE = "pre_judge"
HOOK_POST_JUDGE = "post_judge"
HOOK_PRE_TOOL = "pre_tool"
HOOK_POST_TOOL = "post_tool"
HOOK_TASK_CREATED = "task_created"
HOOK_TASK_COMPLETED = "task_completed"
HOOK_PLUGIN_LOADED = "plugin_loaded"
HOOK_PLUGIN_UNLOADED = "plugin_unloaded"

BUILTIN_HOOKS: frozenset[str] = frozenset(
    {
        HOOK_PRE_AGENT_RUN,
        HOOK_POST_AGENT_RUN,
        HOOK_PRE_JUDGE,
        HOOK_POST_JUDGE,
        HOOK_PRE_TOOL,
        HOOK_POST_TOOL,
        HOOK_TASK_CREATED,
        HOOK_TASK_COMPLETED,
        HOOK_PLUGIN_LOADED,
        HOOK_PLUGIN_UNLOADED,
    }
)


@dataclass
class PluginMeta:
    """Static descriptor for a plugin package or module."""

    name: str
    version: str = "0.1.0"
    plugin_type: PluginType = PluginType.HOOK
    description: str = ""
    author: str = ""
    # Optional registration keys (runner type, judge name, tool name)
    provides: list[str] = field(default_factory=list)
    # Extra metadata (homepage, tags, …)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "plugin_type": self.plugin_type.value
            if isinstance(self.plugin_type, PluginType)
            else str(self.plugin_type),
            "description": self.description,
            "author": self.author,
            "provides": list(self.provides),
            "extra": dict(self.extra),
        }


@dataclass
class PluginContext:
    """Runtime context injected into plugin lifecycle methods."""

    config: dict[str, Any] = field(default_factory=dict)
    # Lazy accessors filled by manager
    register_runner: Callable[..., None] | None = None
    register_judge: Callable[..., None] | None = None
    register_tool: Callable[..., None] | None = None
    register_hook: Callable[..., None] | None = None
    logger: Any = None


class BasePlugin(ABC):
    """Third-party extension base class.

    Subclasses implement lifecycle hooks and register capabilities via
    :class:`PluginContext` during ``on_load`` / ``on_activate``.
    """

    meta: PluginMeta

    def __init__(self, meta: PluginMeta | None = None) -> None:
        if meta is not None:
            self.meta = meta
        elif not hasattr(self, "meta") or self.meta is None:
            raise TypeError(f"{type(self).__name__} requires PluginMeta")

    def on_load(self, ctx: PluginContext) -> None:
        """Called once after the class is imported and instantiated."""

    def on_activate(self, ctx: PluginContext) -> None:
        """Called when the plugin becomes active (capabilities registered)."""

    def on_deactivate(self, ctx: PluginContext) -> None:
        """Called when the plugin is disabled but still loaded."""

    def on_unload(self, ctx: PluginContext) -> None:
        """Called before the plugin instance is discarded."""

    def get_config_schema(self) -> dict[str, Any]:
        """Optional JSON-schema-like dict for UI / validation."""
        return {}


# ---------------------------------------------------------------------------
# Capability registration helpers (typed factories)
# ---------------------------------------------------------------------------


class AgentRunnerFactory:
    """Callable that builds a BaseAgentRunner from agent_config."""

    def __init__(self, factory: Callable[[dict[str, Any]], Any]) -> None:
        self.factory = factory

    def __call__(self, agent_config: dict[str, Any] | None = None) -> Any:
        return self.factory(dict(agent_config or {}))


class JudgeFactory:
    """Callable that builds a BaseJudge instance."""

    def __init__(self, factory: Callable[[], Any]) -> None:
        self.factory = factory

    def __call__(self) -> Any:
        return self.factory()


@dataclass
class ToolSpec:
    """Plugin-provided sandbox tool."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    fn: Callable[..., str] | None = None
    network: bool = False
    source_plugin: str = ""

    def to_builtin_meta(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "parameters": self.parameters,
            "required": list(self.required),
            "fn": self.fn,
            "network": self.network,
            "plugin": self.source_plugin,
        }
