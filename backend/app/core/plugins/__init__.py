# (c) 2026 AgentFlow-Eval
"""Extensible plugin system for AgentFlow-Eval.

Public API
----------
- :func:`get_plugin_manager` — lifecycle (load / activate / unload)
- :func:`get_hook_registry` — pre/post pipeline hooks
- :func:`get_capability_registry` — runners / judges / tools
- :func:`get_plugin_market` — optional local catalog

See ``docs/plugins.md`` for authoring guide.
"""

from app.core.plugins.base import (
    BUILTIN_HOOKS,
    HOOK_PLUGIN_LOADED,
    HOOK_PLUGIN_UNLOADED,
    HOOK_POST_AGENT_RUN,
    HOOK_POST_JUDGE,
    HOOK_POST_TOOL,
    HOOK_PRE_AGENT_RUN,
    HOOK_PRE_JUDGE,
    HOOK_PRE_TOOL,
    HOOK_TASK_COMPLETED,
    HOOK_TASK_CREATED,
    AgentRunnerFactory,
    BasePlugin,
    JudgeFactory,
    PluginContext,
    PluginMeta,
    PluginState,
    PluginType,
    ToolSpec,
)
from app.core.plugins.hooks import HookRegistry, get_hook_registry, reset_hook_registry
from app.core.plugins.loader import PluginLoadError
from app.core.plugins.manager import (
    PluginManager,
    PluginRecord,
    get_plugin_manager,
    reset_plugin_manager,
)
from app.core.plugins.market import (
    MarketEntry,
    PluginMarket,
    get_plugin_market,
    reset_plugin_market,
)
from app.core.plugins.registry import (
    PluginCapabilityRegistry,
    get_capability_registry,
    reset_capability_registry,
)

__all__ = [
    "BUILTIN_HOOKS",
    "HOOK_PLUGIN_LOADED",
    "HOOK_PLUGIN_UNLOADED",
    "HOOK_POST_AGENT_RUN",
    "HOOK_POST_JUDGE",
    "HOOK_POST_TOOL",
    "HOOK_PRE_AGENT_RUN",
    "HOOK_PRE_JUDGE",
    "HOOK_PRE_TOOL",
    "HOOK_TASK_COMPLETED",
    "HOOK_TASK_CREATED",
    "AgentRunnerFactory",
    "BasePlugin",
    "JudgeFactory",
    "PluginContext",
    "PluginMeta",
    "PluginState",
    "PluginType",
    "ToolSpec",
    "HookRegistry",
    "get_hook_registry",
    "reset_hook_registry",
    "PluginLoadError",
    "PluginManager",
    "PluginRecord",
    "get_plugin_manager",
    "reset_plugin_manager",
    "MarketEntry",
    "PluginMarket",
    "get_plugin_market",
    "reset_plugin_market",
    "PluginCapabilityRegistry",
    "get_capability_registry",
    "reset_capability_registry",
]
