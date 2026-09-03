# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory tool capability registry."""

from __future__ import annotations

import threading

from app.runtime.tool_registry.models import ToolCapability


class InMemoryToolRegistry:
    """Thread-safe dict-backed tool capability registry."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolCapability] = {}
        self._lock = threading.Lock()

    def register(self, tool: ToolCapability) -> None:
        with self._lock:
            self._tools[tool.tool_name] = tool

    def get(self, tool_name: str) -> ToolCapability | None:
        with self._lock:
            return self._tools.get(tool_name)

    def list_tools(self) -> list[ToolCapability]:
        with self._lock:
            return list(self._tools.values())

    def remove(self, tool_name: str) -> None:
        with self._lock:
            self._tools.pop(tool_name, None)
