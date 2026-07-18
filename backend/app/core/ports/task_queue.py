# (c) 2026 AgentFlow-Eval
"""Task queue port — abstract async job dispatch (Celery / Eager / Memory / Arq)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class EnqueueResult:
    """Result of enqueueing a background job."""

    task_id: str
    backend: str
    eager: bool = False


@runtime_checkable
class TaskQueuePort(Protocol):
    """Pluggable job queue.

    ``name`` is a logical task name registered by the active adapter
    (e.g. ``run_full_evaluation``).
    """

    @property
    def backend_name(self) -> str:
        """Adapter identifier: celery | eager | memory | arq."""
        ...

    def is_eager(self) -> bool:
        """True when jobs run in-process (no broker required)."""
        ...

    def enqueue(
        self,
        name: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        countdown: float = 0.0,
    ) -> EnqueueResult:
        """Submit a job; returns opaque task id for revoke/tracking."""
        ...

    def revoke(self, task_id: str, *, terminate: bool = True) -> None:
        """Best-effort cancel of a running/queued job."""
        ...
