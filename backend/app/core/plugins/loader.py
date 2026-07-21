# (c) 2026 AgentFlow-Eval
"""Dynamic plugin discovery and import.

Supported sources
-----------------
1. **Python entry** — ``module.path:ClassName`` or ``module.path`` (uses ``Plugin``)
2. **Directory** — each child folder with ``plugin.py`` / ``__init__.py`` / ``plugin.json``
3. **JSON catalog** — list of entry strings for market / batch install
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Type

from app.core.plugins.base import BasePlugin, PluginMeta, PluginType

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredPlugin:
    """A plugin candidate before load."""

    plugin_id: str
    entry: str
    source: str  # "module" | "path" | "catalog"
    path: str | None = None
    manifest: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class PluginLoadError(Exception):
    """Raised when a plugin cannot be imported or validated."""


def parse_entry(entry: str) -> tuple[str, str | None]:
    """Split ``module:attr`` into (module, attr). attr may be None."""
    entry = (entry or "").strip()
    if not entry:
        raise PluginLoadError("empty plugin entry")
    if ":" in entry:
        mod, attr = entry.rsplit(":", 1)
        return mod.strip(), attr.strip() or None
    return entry, None


def import_symbol(entry: str) -> Any:
    """Import ``module`` or ``module:Class``."""
    module_name, attr = parse_entry(entry)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise PluginLoadError(f"import failed for {module_name!r}: {exc}") from exc
    if attr is None:
        # Prefer Plugin / plugin class attributes
        for name in ("Plugin", "plugin", "PLUGIN"):
            if hasattr(module, name):
                return getattr(module, name)
        raise PluginLoadError(
            f"module {module_name!r} has no Plugin/plugin export; use module:Class"
        )
    if not hasattr(module, attr):
        raise PluginLoadError(f"{module_name!r} has no attribute {attr!r}")
    return getattr(module, attr)


def load_plugin_class(entry: str) -> Type[BasePlugin]:
    """Resolve entry to a BasePlugin subclass (or factory returning instance)."""
    obj = import_symbol(entry)
    if isinstance(obj, type) and issubclass(obj, BasePlugin):
        return obj
    if callable(obj) and not isinstance(obj, type):
        # Factory → wrap later
        raise PluginLoadError(
            f"entry {entry!r} is a factory callable; use instantiate_plugin()"
        )
    raise PluginLoadError(
        f"entry {entry!r} is not a BasePlugin subclass (got {type(obj)!r})"
    )


def instantiate_plugin(entry: str, config: dict[str, Any] | None = None) -> BasePlugin:
    """Import and create a plugin instance."""
    obj = import_symbol(entry)
    config = dict(config or {})

    if isinstance(obj, type) and issubclass(obj, BasePlugin):
        try:
            return obj()  # type: ignore[call-arg]
        except TypeError:
            return obj(config=config)  # type: ignore[call-arg]

    if isinstance(obj, BasePlugin):
        return obj

    if callable(obj):
        instance = obj(config) if config else obj()
        if isinstance(instance, BasePlugin):
            return instance
        raise PluginLoadError(f"factory {entry!r} did not return BasePlugin")

    raise PluginLoadError(f"cannot instantiate plugin from {entry!r}")


def load_module_from_path(path: Path, module_name: str | None = None) -> Any:
    """Load a Python file or package directory as a module."""
    path = path.resolve()
    if path.is_dir():
        init = path / "__init__.py"
        plugin_py = path / "plugin.py"
        if plugin_py.exists():
            target = plugin_py
        elif init.exists():
            target = init
        else:
            raise PluginLoadError(f"no plugin.py or __init__.py in {path}")
    else:
        target = path

    name = module_name or f"agentflow_plugin_{path.stem}_{abs(hash(str(path))) % 10**8}"
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"cannot create import spec for {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise PluginLoadError(f"exec_module failed for {target}: {exc}") from exc
    return module


def instantiate_from_path(
    path: Path, config: dict[str, Any] | None = None
) -> BasePlugin:
    """Load plugin from a filesystem path."""
    path = Path(path)
    manifest: dict[str, Any] = {}
    if path.is_dir() and (path / "plugin.json").exists():
        try:
            manifest = json.loads((path / "plugin.json").read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Invalid plugin.json in %s: %s", path, exc)

    module = load_module_from_path(path if path.is_dir() else path.parent / path.name)
    entry_attr = manifest.get("entry") or "Plugin"
    if hasattr(module, entry_attr):
        obj = getattr(module, entry_attr)
    elif hasattr(module, "Plugin"):
        obj = module.Plugin
    elif hasattr(module, "plugin"):
        obj = module.plugin
    else:
        raise PluginLoadError(f"no Plugin export in {path}")

    if isinstance(obj, type) and issubclass(obj, BasePlugin):
        try:
            return obj()
        except TypeError:
            return obj(config=config or {})  # type: ignore[call-arg]
    if isinstance(obj, BasePlugin):
        return obj
    if callable(obj):
        inst = obj(config or {})
        if isinstance(inst, BasePlugin):
            return inst
    raise PluginLoadError(f"invalid plugin object in {path}")


def discover_directory(directory: str | Path) -> list[DiscoveredPlugin]:
    """Scan a directory for plugin packages."""
    root = Path(directory)
    found: list[DiscoveredPlugin] = []
    if not root.is_dir():
        logger.debug("Plugin directory missing: %s", root)
        return found

    for child in sorted(root.iterdir()):
        if child.name.startswith((".", "_")):
            continue
        if child.is_file() and child.suffix == ".py":
            plugin_id = child.stem
            found.append(
                DiscoveredPlugin(
                    plugin_id=plugin_id,
                    entry=str(child.resolve()),
                    source="path",
                    path=str(child.resolve()),
                )
            )
            continue
        if not child.is_dir():
            continue
        has_code = (child / "plugin.py").exists() or (child / "__init__.py").exists()
        if not has_code and not (child / "plugin.json").exists():
            continue
        manifest: dict[str, Any] = {}
        if (child / "plugin.json").exists():
            try:
                manifest = json.loads(
                    (child / "plugin.json").read_text(encoding="utf-8")
                )
            except Exception as exc:
                found.append(
                    DiscoveredPlugin(
                        plugin_id=child.name,
                        entry=str(child.resolve()),
                        source="path",
                        path=str(child.resolve()),
                        error=f"plugin.json: {exc}",
                    )
                )
                continue
        plugin_id = str(manifest.get("name") or child.name)
        found.append(
            DiscoveredPlugin(
                plugin_id=plugin_id,
                entry=str(child.resolve()),
                source="path",
                path=str(child.resolve()),
                manifest=manifest,
            )
        )
    return found


def discover_modules(entries: list[str] | str | None) -> list[DiscoveredPlugin]:
    """Parse comma-separated or list of module:Class entries."""
    if entries is None:
        return []
    if isinstance(entries, str):
        parts = [p.strip() for p in entries.replace(";", ",").split(",") if p.strip()]
    else:
        parts = [str(p).strip() for p in entries if str(p).strip()]
    out: list[DiscoveredPlugin] = []
    for entry in parts:
        try:
            mod, attr = parse_entry(entry)
            plugin_id = (attr or mod.split(".")[-1]).lower()
        except PluginLoadError as exc:
            out.append(
                DiscoveredPlugin(
                    plugin_id=entry,
                    entry=entry,
                    source="module",
                    error=str(exc),
                )
            )
            continue
        out.append(
            DiscoveredPlugin(
                plugin_id=plugin_id,
                entry=entry,
                source="module",
            )
        )
    return out


def meta_from_manifest(data: dict[str, Any], fallback_name: str) -> PluginMeta:
    """Build PluginMeta from plugin.json dict."""
    ptype_raw = str(data.get("type") or data.get("plugin_type") or "hook").lower()
    try:
        ptype = PluginType(ptype_raw)
    except ValueError:
        ptype = PluginType.HOOK
    provides = data.get("provides") or []
    if isinstance(provides, str):
        provides = [provides]
    return PluginMeta(
        name=str(data.get("name") or fallback_name),
        version=str(data.get("version") or "0.1.0"),
        plugin_type=ptype,
        description=str(data.get("description") or ""),
        author=str(data.get("author") or ""),
        provides=list(provides),
        extra={
            k: v
            for k, v in data.items()
            if k
            not in {
                "name",
                "version",
                "type",
                "plugin_type",
                "description",
                "author",
                "provides",
                "entry",
            }
        },
    )
