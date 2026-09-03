# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime execution hook manager interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.hooks.hook import RuntimeHook
from app.runtime.hooks.models import RuntimeHookEvent


class RuntimeHookManager(Protocol):
    """Dispatches runtime lifecycle hook events to registered hooks."""

    def register_hook(self, hook: RuntimeHook) -> None:
        """Register a runtime hook."""

    def remove_hook(self, hook: RuntimeHook) -> None:
        """Remove a registered runtime hook."""

    def list_hooks(self) -> list[RuntimeHook]:
        """Return registered hooks in dispatch order."""

    def dispatch(self, event: RuntimeHookEvent) -> None:
        """Dispatch one lifecycle event to all registered hooks."""
