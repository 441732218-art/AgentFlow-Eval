# (c) 2026 AgentFlow-Eval
"""Optional local plugin marketplace / catalog.

This is intentionally lightweight: no remote network install by default.
Operators place packages under a plugins directory or list modules in config.
The catalog file documents available plugins and install metadata.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.plugins.manager import PluginManager, get_plugin_manager

logger = logging.getLogger(__name__)


@dataclass
class MarketEntry:
    """One catalog listing."""

    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    plugin_type: str = "hook"
    entry: str = ""  # module:Class
    path: str = ""  # relative path under plugins dir
    tags: list[str] = field(default_factory=list)
    homepage: str = ""
    installed: bool = False
    active: bool = False
    # Optional commerce / sandbox overlays (seeded catalog)
    commerce: dict[str, Any] = field(default_factory=dict)
    sandbox: dict[str, Any] = field(default_factory=dict)
    requires_core: str = ">=0.1.0"

    def to_dict(self) -> dict[str, Any]:
        from app.core.plugins.commerce import PluginCommerceMeta

        commerce = PluginCommerceMeta.from_mapping(self.commerce)
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type,
            "entry": self.entry,
            "path": self.path,
            "tags": list(self.tags),
            "homepage": self.homepage,
            "installed": self.installed,
            "active": self.active,
            "is_paid": commerce.is_paid or commerce.price_cents > 0,
            "price_cents": commerce.price_cents,
            "requires_core": self.requires_core,
        }


class PluginMarket:
    """Local catalog + install/enable helpers."""

    def __init__(
        self,
        catalog_path: str | Path | None = None,
        *,
        manager: PluginManager | None = None,
        plugins_dir: str | Path | None = None,
    ) -> None:
        self.catalog_path = Path(catalog_path) if catalog_path else None
        self.plugins_dir = Path(plugins_dir) if plugins_dir else None
        self.manager = manager or get_plugin_manager()
        self._entries: dict[str, MarketEntry] = {}

    def load_catalog(self, path: str | Path | None = None) -> list[MarketEntry]:
        """Load catalog JSON: ``{"plugins": [ {...}, ... ]}`` or a bare list."""
        p = Path(path) if path else self.catalog_path
        self._entries.clear()
        if p is None or not p.is_file():
            return []
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read plugin catalog %s: %s", p, exc)
            return []

        items = raw.get("plugins") if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            return []

        for item in items:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("id") or item.get("name") or "").strip()
            if not mid:
                continue
            tags = item.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            entry = MarketEntry(
                id=mid,
                name=str(item.get("name") or mid),
                version=str(item.get("version") or "0.1.0"),
                description=str(item.get("description") or ""),
                author=str(item.get("author") or ""),
                plugin_type=str(item.get("type") or item.get("plugin_type") or "hook"),
                entry=str(item.get("entry") or ""),
                path=str(item.get("path") or ""),
                tags=list(tags),
                homepage=str(item.get("homepage") or ""),
            )
            self._entries[mid] = entry

        self._refresh_install_flags()
        return list(self._entries.values())

    def _refresh_install_flags(self) -> None:
        installed_ids = {p["plugin_id"] for p in self.manager.list_plugins()}
        for e in self._entries.values():
            e.installed = e.id in installed_ids or e.name in installed_ids
            rec = self.manager.get(e.id) or self.manager.get(e.name)
            e.active = bool(rec and rec.state.value == "active")

    def list_catalog(
        self,
        *,
        tag: str | None = None,
        plugin_type: str | None = None,
        installed_only: bool = False,
    ) -> list[dict[str, Any]]:
        self._refresh_install_flags()
        out = []
        for e in sorted(self._entries.values(), key=lambda x: x.id):
            if tag and tag not in e.tags:
                continue
            if plugin_type and e.plugin_type != plugin_type:
                continue
            if installed_only and not e.installed:
                continue
            out.append(e.to_dict())
        return out

    def install(
        self,
        catalog_id: str,
        *,
        activate: bool = True,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Install from catalog by loading module entry or local path."""
        entry = self._entries.get(catalog_id)
        if entry is None:
            raise KeyError(f"catalog entry not found: {catalog_id}")

        if entry.entry:
            rec = self.manager.load(
                plugin_id=entry.id,
                entry=entry.entry,
                config=config,
                activate=activate,
            )
        elif entry.path:
            base = self.plugins_dir or Path(".")
            target = Path(entry.path)
            if not target.is_absolute():
                target = base / target
            rec = self.manager.load(
                plugin_id=entry.id,
                path=target,
                config=config,
                activate=activate,
            )
        else:
            raise ValueError(f"catalog entry {catalog_id} has no entry or path")

        self._refresh_install_flags()
        return rec.to_dict()

    def uninstall(self, catalog_id: str) -> dict[str, Any]:
        rec = self.manager.get(catalog_id)
        if rec is None:
            # try name match from catalog
            entry = self._entries.get(catalog_id)
            if entry:
                rec = self.manager.get(entry.name)
        if rec is None:
            raise KeyError(f"plugin not installed: {catalog_id}")
        out = self.manager.unload(rec.plugin_id).to_dict()
        self._refresh_install_flags()
        return out

    def seed_builtin_catalog(self) -> list[MarketEntry]:
        """In-memory catalog of example plugins shipped with the project."""
        free_commerce = {
            "price_cents": 0,
            "license": "MIT",
            "entitlement_plan": ["free", "pro", "enterprise"],
        }
        free_sandbox = {"allow_network": False, "permissions": []}
        builtins = [
            MarketEntry(
                id="echo_tool",
                name="echo_tool",
                version="1.0.0",
                description="Example tool plugin that echoes arguments as JSON.",
                author="AgentFlow-Eval",
                plugin_type="tool",
                entry="app.plugins.examples.echo_tool:Plugin",
                tags=["example", "tool", "free"],
                commerce=dict(free_commerce),
                sandbox=dict(free_sandbox),
            ),
            MarketEntry(
                id="length_judge",
                name="length_judge",
                version="1.0.0",
                description="Example rule judge scoring answer length vs expected.",
                author="AgentFlow-Eval",
                plugin_type="judge",
                entry="app.plugins.examples.length_judge:Plugin",
                tags=["example", "judge", "free"],
                commerce=dict(free_commerce),
                sandbox=dict(free_sandbox),
            ),
            MarketEntry(
                id="echo_runner",
                name="echo_runner",
                version="1.0.0",
                description="Example AgentRunner that returns the query as final answer.",
                author="AgentFlow-Eval",
                plugin_type="agent_runner",
                entry="app.plugins.examples.echo_runner:Plugin",
                tags=["example", "runner", "free"],
                commerce=dict(free_commerce),
                sandbox=dict(free_sandbox),
            ),
            MarketEntry(
                id="audit_hooks",
                name="audit_hooks",
                version="1.0.0",
                description="Example hook plugin logging pre/post agent and judge events.",
                author="AgentFlow-Eval",
                plugin_type="hook",
                entry="app.plugins.examples.audit_hooks:Plugin",
                tags=["example", "hook", "free"],
                commerce=dict(free_commerce),
                sandbox=dict(free_sandbox),
            ),
            # Paid mock — pro/enterprise only (no real payment channel)
            MarketEntry(
                id="premium_length_judge",
                name="premium_length_judge",
                version="1.0.0",
                description="Paid mock: same LengthJudge, pro/enterprise entitlement only.",
                author="AgentFlow-Eval",
                plugin_type="judge",
                entry="app.plugins.examples.length_judge:Plugin",
                tags=["example", "judge", "paid", "premium"],
                commerce={
                    "price_cents": 1999,
                    "currency": "USD",
                    "license": "proprietary",
                    "entitlement_plan": ["pro", "enterprise"],
                    "is_paid": True,
                    "trial_days": 0,
                },
                sandbox={
                    "allow_network": False,
                    "permissions": ["system:config"],
                    "max_cpu_ms": 60_000,
                },
                requires_core=">=0.1.0",
            ),
        ]
        for e in builtins:
            self._entries[e.id] = e
        self._refresh_install_flags()
        return builtins

    def commerce_for(self, catalog_id: str) -> dict[str, Any]:
        """Return version + commerce + sandbox metadata for a catalog entry."""
        from app.core.plugins.commerce import PluginCommerceMeta
        from app.core.plugins.sandbox import PluginSandboxPolicy
        from app.core.plugins.versioning import plugin_version_info

        entry = self._entries.get(catalog_id)
        if entry is None:
            raise KeyError(catalog_id)
        commerce = PluginCommerceMeta.from_mapping(entry.commerce or None)
        if not entry.commerce:
            commerce = PluginCommerceMeta(
                price_cents=0,
                license="MIT",
                entitlement_plan=["free", "pro", "enterprise"],
            )
        sandbox = PluginSandboxPolicy.from_mapping(entry.sandbox or None)
        ver = plugin_version_info(
            {
                "version": entry.version,
                "requires_core": entry.requires_core or ">=0.1.0",
            }
        )
        return {
            "id": entry.id,
            "name": entry.name,
            "plugin_type": entry.plugin_type,
            "entry": entry.entry,
            "tags": list(entry.tags),
            "commerce": commerce.to_dict(),
            "sandbox": sandbox.to_dict(),
            "version": ver,
            "requires_core": entry.requires_core,
            "installed": entry.installed,
            "active": entry.active,
        }


_market: PluginMarket | None = None


def get_plugin_market() -> PluginMarket:
    global _market
    if _market is None:
        _market = PluginMarket()
    return _market


def reset_plugin_market() -> PluginMarket:
    global _market
    _market = PluginMarket(manager=get_plugin_manager())
    return _market
