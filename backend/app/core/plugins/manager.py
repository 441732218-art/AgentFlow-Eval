# (c) 2026 AgentFlow-Eval
"""Plugin lifecycle manager — discover, load, activate, deactivate, unload."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.plugins.base import (
    BasePlugin,
    PluginContext,
    PluginMeta,
    PluginState,
    PluginType,
    ToolSpec,
    HOOK_PLUGIN_LOADED,
    HOOK_PLUGIN_UNLOADED,
)
from app.core.plugins.hooks import HookRegistry, get_hook_registry
from app.core.plugins.loader import (
    DiscoveredPlugin,
    PluginLoadError,
    discover_directory,
    discover_modules,
    instantiate_from_path,
    instantiate_plugin,
)
from app.core.plugins.registry import (
    PluginCapabilityRegistry,
    get_capability_registry,
)

logger = logging.getLogger(__name__)


@dataclass
class PluginRecord:
    """Runtime bookkeeping for one plugin."""

    plugin_id: str
    entry: str
    source: str
    state: PluginState = PluginState.DISCOVERED
    meta: PluginMeta | None = None
    instance: BasePlugin | None = None
    error: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    path: str | None = None
    hook_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "entry": self.entry,
            "source": self.source,
            "state": self.state.value,
            "meta": self.meta.to_dict() if self.meta else None,
            "error": self.error,
            "path": self.path,
            "config": dict(self.config),
            "plugin_type": (
                self.meta.plugin_type.value
                if self.meta and isinstance(self.meta.plugin_type, PluginType)
                else (self.meta.plugin_type if self.meta else None)
            ),
        }


class PluginManager:
    """Owns discovery, lifecycle, and capability registration."""

    def __init__(
        self,
        *,
        hooks: HookRegistry | None = None,
        capabilities: PluginCapabilityRegistry | None = None,
    ) -> None:
        self.hooks = hooks or get_hook_registry()
        self.capabilities = capabilities or get_capability_registry()
        self._plugins: dict[str, PluginRecord] = {}
        self._enabled: bool = True

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _make_context(self, plugin_id: str, config: dict[str, Any]) -> PluginContext:
        pid = plugin_id

        def _reg_runner(key: str, factory: Any) -> None:
            self.capabilities.register_runner(key, factory, plugin_id=pid)

        def _reg_judge(key: str, factory: Any) -> None:
            self.capabilities.register_judge(key, factory, plugin_id=pid)

        def _reg_tool(
            name: str,
            fn: Any,
            *,
            description: str = "",
            parameters: dict[str, Any] | None = None,
            required: list[str] | None = None,
            network: bool = False,
            spec: ToolSpec | None = None,
        ) -> None:
            if spec is not None:
                self.capabilities.register_tool(spec, plugin_id=pid)
                return
            self.capabilities.register_tool(
                ToolSpec(
                    name=name,
                    description=description or f"Plugin tool {name}",
                    parameters=parameters or {},
                    required=list(required or []),
                    fn=fn,
                    network=network,
                    source_plugin=pid,
                ),
                plugin_id=pid,
            )

        def _reg_hook(
            hook_name: str,
            callback: Any,
            *,
            priority: int = 100,
        ) -> int:
            entry_id = self.hooks.register(
                hook_name, callback, priority=priority, plugin_id=pid
            )
            rec = self._plugins.get(pid)
            if rec is not None:
                rec.hook_ids.append(entry_id)
            return entry_id

        return PluginContext(
            config=dict(config),
            register_runner=_reg_runner,
            register_judge=_reg_judge,
            register_tool=_reg_tool,
            register_hook=_reg_hook,
            logger=logging.getLogger(f"plugin.{pid}"),
        )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(
        self,
        *,
        directories: list[str] | None = None,
        modules: list[str] | str | None = None,
    ) -> list[PluginRecord]:
        """Discover plugins without loading code (path/module scan)."""
        discovered: list[DiscoveredPlugin] = []
        for d in directories or []:
            discovered.extend(discover_directory(d))
        discovered.extend(discover_modules(modules))

        records: list[PluginRecord] = []
        for d in discovered:
            existing = self._plugins.get(d.plugin_id)
            if existing and existing.state in {
                PluginState.LOADED,
                PluginState.ACTIVE,
            }:
                records.append(existing)
                continue
            rec = PluginRecord(
                plugin_id=d.plugin_id,
                entry=d.entry,
                source=d.source,
                state=PluginState.ERROR if d.error else PluginState.DISCOVERED,
                error=d.error,
                path=d.path,
            )
            if d.manifest:
                from app.core.plugins.loader import meta_from_manifest

                rec.meta = meta_from_manifest(d.manifest, d.plugin_id)
            self._plugins[d.plugin_id] = rec
            records.append(rec)
        return records

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(
        self,
        plugin_id: str | None = None,
        *,
        entry: str | None = None,
        path: str | Path | None = None,
        config: dict[str, Any] | None = None,
        activate: bool = True,
    ) -> PluginRecord:
        """Load (and optionally activate) a plugin by id, entry, or path."""
        if not self._enabled:
            raise RuntimeError("Plugin system is disabled")

        config = dict(config or {})
        rec: PluginRecord | None = None

        if plugin_id and plugin_id in self._plugins:
            rec = self._plugins[plugin_id]
            entry = entry or rec.entry
            path = path or rec.path
            if not config and rec.config:
                config = dict(rec.config)

        if path is not None:
            path = Path(path)
            pid = plugin_id or path.stem if path.is_file() else (plugin_id or path.name)
            try:
                instance = instantiate_from_path(path, config)
            except PluginLoadError as exc:
                rec = PluginRecord(
                    plugin_id=pid,
                    entry=str(path),
                    source="path",
                    state=PluginState.ERROR,
                    error=str(exc),
                    path=str(path),
                    config=config,
                )
                self._plugins[pid] = rec
                return rec
            rec = PluginRecord(
                plugin_id=instance.meta.name or pid,
                entry=str(path),
                source="path",
                path=str(path),
                config=config,
                instance=instance,
                meta=instance.meta,
                state=PluginState.LOADED,
            )
        elif entry:
            try:
                instance = instantiate_plugin(entry, config)
            except PluginLoadError as exc:
                pid = plugin_id or entry
                rec = PluginRecord(
                    plugin_id=pid,
                    entry=entry,
                    source="module",
                    state=PluginState.ERROR,
                    error=str(exc),
                    config=config,
                )
                self._plugins[pid] = rec
                return rec
            rec = PluginRecord(
                plugin_id=instance.meta.name or plugin_id or entry,
                entry=entry,
                source="module",
                config=config,
                instance=instance,
                meta=instance.meta,
                state=PluginState.LOADED,
            )
        elif rec and rec.entry:
            return self.load(
                rec.plugin_id,
                entry=rec.entry if rec.source == "module" else None,
                path=rec.path if rec.source == "path" else (
                    rec.entry if rec.source == "path" else None
                ),
                config=config,
                activate=activate,
            )
        else:
            raise PluginLoadError("load() requires plugin_id, entry, or path")

        self._plugins[rec.plugin_id] = rec
        assert rec.instance is not None
        ctx = self._make_context(rec.plugin_id, config)
        try:
            rec.instance.on_load(ctx)
        except Exception as exc:
            rec.state = PluginState.ERROR
            rec.error = f"on_load: {exc}"
            logger.exception("Plugin %s on_load failed", rec.plugin_id)
            return rec

        if activate:
            return self.activate(rec.plugin_id)
        return rec

    def activate(self, plugin_id: str) -> PluginRecord:
        rec = self._require(plugin_id)
        if rec.instance is None:
            rec.state = PluginState.ERROR
            rec.error = "no instance"
            return rec
        if rec.state == PluginState.ACTIVE:
            return rec
        ctx = self._make_context(plugin_id, rec.config)
        try:
            rec.instance.on_activate(ctx)
            rec.state = PluginState.ACTIVE
            rec.error = None
        except Exception as exc:
            rec.state = PluginState.ERROR
            rec.error = f"on_activate: {exc}"
            logger.exception("Plugin %s on_activate failed", plugin_id)
            return rec
        try:
            self.hooks.emit_sync(
                HOOK_PLUGIN_LOADED,
                {"plugin_id": plugin_id, "meta": rec.meta.to_dict() if rec.meta else {}},
            )
        except Exception:
            pass
        logger.info("Plugin activated: %s", plugin_id)
        return rec

    def deactivate(self, plugin_id: str) -> PluginRecord:
        rec = self._require(plugin_id)
        if rec.instance is None:
            return rec
        ctx = self._make_context(plugin_id, rec.config)
        try:
            rec.instance.on_deactivate(ctx)
        except Exception as exc:
            logger.exception("Plugin %s on_deactivate failed: %s", plugin_id, exc)
        # Drop capabilities but keep instance loaded
        self.capabilities.unregister_runners(plugin_id)
        self.capabilities.unregister_judges(plugin_id)
        self.capabilities.unregister_tools(plugin_id)
        self.hooks.unregister_plugin(plugin_id)
        rec.hook_ids.clear()
        rec.state = PluginState.DISABLED
        logger.info("Plugin deactivated: %s", plugin_id)
        return rec

    def unload(self, plugin_id: str) -> PluginRecord:
        rec = self._require(plugin_id)
        if rec.state == PluginState.ACTIVE:
            self.deactivate(plugin_id)
        if rec.instance is not None:
            ctx = self._make_context(plugin_id, rec.config)
            try:
                rec.instance.on_unload(ctx)
            except Exception as exc:
                logger.exception("Plugin %s on_unload failed: %s", plugin_id, exc)
        try:
            self.hooks.emit_sync(
                HOOK_PLUGIN_UNLOADED,
                {"plugin_id": plugin_id},
            )
        except Exception:
            pass
        rec.instance = None
        rec.state = PluginState.UNLOADED
        logger.info("Plugin unloaded: %s", plugin_id)
        return rec

    def reload(self, plugin_id: str) -> PluginRecord:
        rec = self._require(plugin_id)
        entry, path, source, config = rec.entry, rec.path, rec.source, dict(rec.config)
        self.unload(plugin_id)
        if source == "path":
            return self.load(plugin_id, path=path or entry, config=config, activate=True)
        return self.load(plugin_id, entry=entry, config=config, activate=True)

    # ------------------------------------------------------------------
    # Bulk bootstrap
    # ------------------------------------------------------------------

    def bootstrap(
        self,
        *,
        enabled: bool = True,
        directories: list[str] | None = None,
        modules: list[str] | str | None = None,
        auto_activate: bool = True,
        allowlist: list[str] | None = None,
    ) -> dict[str, Any]:
        """Discover and load all configured plugins (app startup).

        ``allowlist``: optional list of allowed entry strings or module prefixes.
        When set, any discovered plugin whose entry does not match is skipped.
        """
        self._enabled = enabled
        if not enabled:
            return {"enabled": False, "loaded": [], "errors": []}

        def _allowed(entry: str, plugin_id: str) -> bool:
            if not allowlist:
                return True
            e = (entry or "").strip()
            pid = (plugin_id or "").strip()
            for a in allowlist:
                a = (a or "").strip()
                if not a:
                    continue
                if e == a or pid == a or e.startswith(a) or a in e:
                    return True
            return False

        self.discover(directories=directories, modules=modules)
        loaded: list[str] = []
        errors: list[dict[str, str]] = []
        skipped: list[str] = []

        # Explicit modules first
        for d in discover_modules(modules):
            if d.error:
                errors.append({"plugin_id": d.plugin_id, "error": d.error})
                continue
            if not _allowed(d.entry, d.plugin_id):
                skipped.append(d.plugin_id)
                logger.warning(
                    "Plugin %s skipped by allowlist (entry=%s)", d.plugin_id, d.entry
                )
                continue
            try:
                rec = self.load(entry=d.entry, activate=auto_activate)
                if rec.state == PluginState.ERROR:
                    errors.append({"plugin_id": rec.plugin_id, "error": rec.error or "error"})
                else:
                    loaded.append(rec.plugin_id)
            except Exception as exc:
                errors.append({"plugin_id": d.plugin_id, "error": str(exc)})

        # Directories
        for directory in directories or []:
            for d in discover_directory(directory):
                if d.plugin_id in loaded:
                    continue
                if d.error:
                    errors.append({"plugin_id": d.plugin_id, "error": d.error})
                    continue
                entry_hint = d.entry or d.path or d.plugin_id
                if not _allowed(str(entry_hint), d.plugin_id):
                    skipped.append(d.plugin_id)
                    logger.warning(
                        "Plugin %s from dir skipped by allowlist", d.plugin_id
                    )
                    continue
                try:
                    rec = self.load(
                        plugin_id=d.plugin_id,
                        path=d.path or d.entry,
                        activate=auto_activate,
                    )
                    if rec.state == PluginState.ERROR:
                        errors.append(
                            {"plugin_id": rec.plugin_id, "error": rec.error or "error"}
                        )
                    else:
                        loaded.append(rec.plugin_id)
                except Exception as exc:
                    errors.append({"plugin_id": d.plugin_id, "error": str(exc)})

        return {
            "enabled": True,
            "loaded": loaded,
            "errors": errors,
            "skipped_allowlist": skipped,
            "total": len(self._plugins),
        }

    def shutdown(self) -> None:
        """Unload all plugins (app shutdown)."""
        for pid in list(self._plugins.keys()):
            try:
                if self._plugins[pid].state in {
                    PluginState.ACTIVE,
                    PluginState.LOADED,
                    PluginState.DISABLED,
                }:
                    self.unload(pid)
            except Exception:
                logger.exception("Failed unloading plugin %s", pid)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, plugin_id: str) -> PluginRecord | None:
        return self._plugins.get(plugin_id)

    def list_plugins(
        self,
        *,
        state: PluginState | str | None = None,
        plugin_type: PluginType | str | None = None,
    ) -> list[dict[str, Any]]:
        items = []
        for rec in self._plugins.values():
            if state is not None:
                sv = state.value if isinstance(state, PluginState) else str(state)
                if rec.state.value != sv:
                    continue
            if plugin_type is not None and rec.meta:
                tv = (
                    plugin_type.value
                    if isinstance(plugin_type, PluginType)
                    else str(plugin_type)
                )
                mt = (
                    rec.meta.plugin_type.value
                    if isinstance(rec.meta.plugin_type, PluginType)
                    else str(rec.meta.plugin_type)
                )
                if mt != tv:
                    continue
            items.append(rec.to_dict())
        items.sort(key=lambda x: x["plugin_id"])
        return items

    def status(self) -> dict[str, Any]:
        by_state: dict[str, int] = {}
        for rec in self._plugins.values():
            by_state[rec.state.value] = by_state.get(rec.state.value, 0) + 1
        return {
            "enabled": self._enabled,
            "plugins": len(self._plugins),
            "by_state": by_state,
            "runners": self.capabilities.list_runners(),
            "judges": self.capabilities.list_judges(),
            "tools": self.capabilities.list_tools(),
            "hooks": self.hooks.list_hooks(),
        }

    def _require(self, plugin_id: str) -> PluginRecord:
        if plugin_id not in self._plugins:
            raise KeyError(f"unknown plugin: {plugin_id}")
        return self._plugins[plugin_id]

    def clear_all(self) -> None:
        """Reset manager (tests)."""
        self.shutdown()
        self._plugins.clear()
        self.capabilities.clear()
        self.hooks.clear()


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------

_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


def reset_plugin_manager() -> PluginManager:
    """Replace singleton (tests)."""
    global _manager
    if _manager is not None:
        try:
            _manager.clear_all()
        except Exception:
            pass
    from app.core.plugins.hooks import reset_hook_registry
    from app.core.plugins.registry import reset_capability_registry

    hooks = reset_hook_registry()
    caps = reset_capability_registry()
    _manager = PluginManager(hooks=hooks, capabilities=caps)
    return _manager
