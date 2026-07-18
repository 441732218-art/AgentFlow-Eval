# (c) 2026 AgentFlow-Eval
"""Cache port — L1/L2 or memory-only depending on deploy profile."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CachePort(Protocol):
    """Minimal async cache interface used by application services."""

    @property
    def backend_name(self) -> str: ...

    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...
