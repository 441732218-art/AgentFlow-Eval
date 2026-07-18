# (c) 2026 AgentFlow-Eval
"""Event bus port — Redis pub/sub or in-process fan-out."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventBusPort(Protocol):
    """Publish domain/activity events across processes (or in-process for lite)."""

    @property
    def backend_name(self) -> str: ...

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        """Sync-safe publish (Celery workers + FastAPI)."""
        ...
