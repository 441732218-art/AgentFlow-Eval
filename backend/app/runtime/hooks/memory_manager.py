# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime hook manager."""

from __future__ import annotations

import threading

from app.runtime.hooks.hook import RuntimeHook
from app.runtime.hooks.models import RuntimeHookEvent

_EVENT_METHODS: dict[str, str] = {
    "execution.started": "before_execution",
    "execution.completed": "after_execution",
    "execution.failed": "on_failure",
    "step.started": "before_step",
    "step.completed": "after_step",
    "step.failed": "on_failure",
    "tool.started": "before_tool",
    "tool.completed": "after_tool",
    "tool.failed": "on_failure",
}


class InMemoryRuntimeHookManager:
    """Thread-safe in-memory runtime hook manager."""

    def __init__(self) -> None:
        self._hooks: list[RuntimeHook] = []
        self._lock = threading.Lock()

    def register_hook(self, hook: RuntimeHook) -> None:
        with self._lock:
            if hook not in self._hooks:
                self._hooks.append(hook)

    def remove_hook(self, hook: RuntimeHook) -> None:
        with self._lock:
            self._hooks = [registered for registered in self._hooks if registered is not hook]

    def list_hooks(self) -> list[RuntimeHook]:
        with self._lock:
            return list(self._hooks)

    def dispatch(self, event: RuntimeHookEvent) -> None:
        method_name = _EVENT_METHODS.get(event.event_type)
        if method_name is None:
            return
        with self._lock:
            hooks = list(self._hooks)
        for hook in hooks:
            try:
                getattr(hook, method_name)(event)
            except Exception:
                continue
