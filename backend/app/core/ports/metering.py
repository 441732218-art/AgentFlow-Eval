# (c) 2026 AgentFlow-Eval
"""Metering port — usage / billing hooks (noop until BILLING_ENABLED)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MeteringPort(Protocol):
    """Record consumable usage (tokens, tasks, judge calls)."""

    @property
    def backend_name(self) -> str: ...

    def record(
        self,
        *,
        actor: str,
        metric: str,
        quantity: float = 1.0,
        ref_type: str | None = None,
        ref_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Best-effort record; must never raise into the business path."""
        ...
