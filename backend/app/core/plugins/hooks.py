# (c) 2026 AgentFlow-Eval
"""Hook registry — ordered pre/post callbacks for core pipeline events."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

HookCallback = Callable[..., Any]


@dataclass(order=True)
class HookEntry:
    """A single registered hook callback with priority (lower runs first)."""

    priority: int
    name: str = field(compare=False)
    callback: HookCallback = field(compare=False)
    plugin_id: str | None = field(default=None, compare=False)
    # Unique id for unregistration
    entry_id: int = field(default=0, compare=False)


class HookRegistry:
    """In-process ordered hook bus.

    Callbacks may be sync or async. Exceptions are isolated (logged) so a bad
    plugin cannot break the host pipeline unless ``strict=True``.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookEntry]] = defaultdict(list)
        self._seq = 0
        self._lock = asyncio.Lock() if False else None  # sync-safe; GIL list ops

    def register(
        self,
        hook_name: str,
        callback: HookCallback,
        *,
        priority: int = 100,
        plugin_id: str | None = None,
    ) -> int:
        """Register a callback. Returns entry id for later unregister."""
        if not hook_name or not callable(callback):
            raise ValueError("hook_name and callable callback are required")
        self._seq += 1
        entry = HookEntry(
            priority=int(priority),
            name=hook_name,
            callback=callback,
            plugin_id=plugin_id,
            entry_id=self._seq,
        )
        self._hooks[hook_name].append(entry)
        self._hooks[hook_name].sort()
        logger.debug(
            "Hook registered: %s priority=%s plugin=%s id=%s",
            hook_name,
            priority,
            plugin_id,
            entry.entry_id,
        )
        return entry.entry_id

    def unregister(self, entry_id: int) -> bool:
        """Remove a hook by entry id. Returns True if found."""
        for name, entries in list(self._hooks.items()):
            for i, e in enumerate(entries):
                if e.entry_id == entry_id:
                    del entries[i]
                    if not entries:
                        del self._hooks[name]
                    return True
        return False

    def unregister_plugin(self, plugin_id: str) -> int:
        """Remove all hooks owned by a plugin. Returns count removed."""
        removed = 0
        for name in list(self._hooks.keys()):
            before = len(self._hooks[name])
            self._hooks[name] = [
                e for e in self._hooks[name] if e.plugin_id != plugin_id
            ]
            removed += before - len(self._hooks[name])
            if not self._hooks[name]:
                del self._hooks[name]
        return removed

    def list_hooks(self, hook_name: str | None = None) -> list[dict[str, Any]]:
        """List registered hooks (for API / debug)."""
        names = [hook_name] if hook_name else sorted(self._hooks.keys())
        out: list[dict[str, Any]] = []
        for name in names:
            for e in self._hooks.get(name, []):
                out.append(
                    {
                        "hook": name,
                        "entry_id": e.entry_id,
                        "priority": e.priority,
                        "plugin_id": e.plugin_id,
                        "callback": getattr(e.callback, "__name__", repr(e.callback)),
                    }
                )
        return out

    def clear(self) -> None:
        self._hooks.clear()

    def emit_sync(
        self,
        hook_name: str,
        payload: dict[str, Any] | None = None,
        *,
        strict: bool = False,
    ) -> list[Any]:
        """Run hooks sequentially (sync path). Async callbacks run via asyncio.run if needed."""
        payload = dict(payload or {})
        results: list[Any] = []
        for entry in list(self._hooks.get(hook_name, [])):
            try:
                result = entry.callback(payload)
                if asyncio.iscoroutine(result):
                    # Avoid asyncio.run() — it closes the loop and breaks
                    # subsequent pytest-asyncio tests. Prefer sync hooks when
                    # calling emit_sync; async hooks should use emit().
                    logger.warning(
                        "Async hook %s/%s skipped in emit_sync; use await emit()",
                        hook_name,
                        entry.entry_id,
                    )
                    result = None
                results.append(result)
            except Exception as exc:
                logger.exception(
                    "Hook %s (plugin=%s) failed: %s",
                    hook_name,
                    entry.plugin_id,
                    exc,
                )
                if strict:
                    raise
                results.append({"error": str(exc), "plugin_id": entry.plugin_id})
        return results

    async def emit(
        self,
        hook_name: str,
        payload: dict[str, Any] | None = None,
        *,
        strict: bool = False,
    ) -> list[Any]:
        """Run hooks sequentially; await async callbacks."""
        payload = dict(payload or {})
        results: list[Any] = []
        for entry in list(self._hooks.get(hook_name, [])):
            try:
                result = entry.callback(payload)
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(result)
            except Exception as exc:
                logger.exception(
                    "Hook %s (plugin=%s) failed: %s",
                    hook_name,
                    entry.plugin_id,
                    exc,
                )
                if strict:
                    raise
                results.append({"error": str(exc), "plugin_id": entry.plugin_id})
        return results


# Process-wide default registry
_default_hooks: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    global _default_hooks
    if _default_hooks is None:
        _default_hooks = HookRegistry()
    return _default_hooks


def reset_hook_registry() -> HookRegistry:
    """Replace the global registry (tests)."""
    global _default_hooks
    _default_hooks = HookRegistry()
    return _default_hooks
