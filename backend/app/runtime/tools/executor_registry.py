# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Registry of executor adapters keyed by ``executor_type``."""

from __future__ import annotations

from app.runtime.tools.adapter import ToolExecutorAdapter


class DuplicateExecutorAdapterError(Exception):
    """Raised when an adapter is registered for an existing ``executor_type``."""

    def __init__(self, executor_type: str) -> None:
        self.executor_type = executor_type
        super().__init__(f"Executor adapter already registered: {executor_type}")


class UnknownExecutorTypeError(Exception):
    """Raised when no adapter is registered for the requested ``executor_type``."""

    def __init__(self, executor_type: str) -> None:
        self.executor_type = executor_type
        super().__init__(f"No executor adapter registered for: {executor_type}")


class ToolExecutorRegistry:
    """Register and resolve ``ToolExecutorAdapter`` instances by ``executor_type``."""

    def __init__(self) -> None:
        self._adapters: dict[str, ToolExecutorAdapter] = {}

    def register(self, adapter: ToolExecutorAdapter) -> None:
        """Register an adapter for its ``executor_type``.

        Raises:
            TypeError: If ``adapter`` is not a ``ToolExecutorAdapter`` instance.
            ValueError: If ``adapter.executor_type`` is empty.
            DuplicateExecutorAdapterError: If the type is already registered.
        """
        if not isinstance(adapter, ToolExecutorAdapter):
            raise TypeError(
                f"Expected ToolExecutorAdapter instance, got {type(adapter).__name__}"
            )
        executor_type = (adapter.executor_type or "").strip()
        if not executor_type:
            raise ValueError("ToolExecutorAdapter.executor_type must be a non-empty string")
        if executor_type in self._adapters:
            raise DuplicateExecutorAdapterError(executor_type)
        self._adapters[executor_type] = adapter

    def get(self, executor_type: str) -> ToolExecutorAdapter | None:
        """Return an adapter for ``executor_type``, or ``None`` if not registered."""
        return self._adapters.get(executor_type)
