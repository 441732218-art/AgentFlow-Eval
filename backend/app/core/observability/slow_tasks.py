# (c) 2026 AgentFlow-Eval
"""Slow-task diagnostics: in-process ring buffer + durable DB persistence."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_MAX = 200
_lock = threading.Lock()
_events: deque[dict[str, Any]] = deque(maxlen=_MAX)


def record_slow_task(
    *,
    stage: str,
    duration_sec: float,
    threshold_sec: float,
    ref_id: str | None = None,
    status: str = "ok",
    extra: dict[str, Any] | None = None,
    actor: str | None = None,
    trace_id: str | None = None,
    persist: bool = True,
) -> bool:
    """Record if duration exceeds threshold. Returns True if recorded.

    Always writes the in-process ring buffer; optionally persists to
    ``slow_task_events`` for cross-restart diagnostics.
    """
    if duration_sec < threshold_sec:
        return False

    if not trace_id:
        try:
            from app.core.observability.tracing import get_trace_id

            trace_id = get_trace_id() or None
        except Exception:
            trace_id = None

    if not actor and extra:
        actor = str(extra.get("actor") or "") or None

    item = {
        "id": str(uuid4()),
        "stage": stage,
        "duration_sec": round(float(duration_sec), 4),
        "threshold_sec": float(threshold_sec),
        "ref_id": ref_id,
        "status": status,
        "at": time.time(),
        "trace_id": trace_id,
        "actor": actor,
        "extra": dict(extra or {}),
    }
    with _lock:
        _events.appendleft(item)

    if persist:
        _persist_async(item)
    return True


def _persist_async(item: dict[str, Any]) -> None:
    """Best-effort DB write without blocking the caller."""
    try:
        import asyncio

        async def _write() -> None:
            from app.core.dependencies import async_session_factory
            from app.models.slow_task import SlowTaskEvent

            async with async_session_factory() as session:
                try:
                    session.add(
                        SlowTaskEvent(
                            id=item.get("id") or str(uuid4()),
                            stage=str(item["stage"]),
                            duration_sec=float(item["duration_sec"]),
                            threshold_sec=float(item["threshold_sec"]),
                            ref_id=item.get("ref_id"),
                            status=str(item.get("status") or "ok"),
                            trace_id=item.get("trace_id"),
                            actor=item.get("actor"),
                            extra=dict(item.get("extra") or {}),
                        )
                    )
                    await session.commit()
                except Exception as exc:
                    await session.rollback()
                    logger.debug("slow_task persist failed: %s", exc)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write())
        except RuntimeError:
            asyncio.run(_write())
    except Exception as exc:
        logger.debug("slow_task persist skipped: %s", exc)


def list_slow_tasks(limit: int = 50) -> list[dict[str, Any]]:
    """In-process samples (fast, process-local)."""
    with _lock:
        return list(_events)[: max(1, min(limit, _MAX))]


async def list_slow_tasks_db(limit: int = 50) -> list[dict[str, Any]]:
    """Durable samples from database (newest first)."""
    from sqlalchemy import select

    from app.core.dependencies import async_session_factory
    from app.models.slow_task import SlowTaskEvent

    limit = max(1, min(int(limit), 500))
    try:
        async with async_session_factory() as session:
            rows = await session.execute(
                select(SlowTaskEvent)
                .order_by(SlowTaskEvent.created_at.desc())
                .limit(limit)
            )
            out: list[dict[str, Any]] = []
            for r in rows.scalars().all():
                out.append(
                    {
                        "id": r.id,
                        "stage": r.stage,
                        "duration_sec": r.duration_sec,
                        "threshold_sec": r.threshold_sec,
                        "ref_id": r.ref_id,
                        "status": r.status,
                        "trace_id": r.trace_id,
                        "actor": r.actor,
                        "extra": r.extra or {},
                        "at": r.created_at.timestamp() if r.created_at else None,
                        "created_at": r.created_at.isoformat()
                        if r.created_at
                        else None,
                        "source": "db",
                    }
                )
            return out
    except Exception as exc:
        logger.debug("list_slow_tasks_db failed, falling back to memory: %s", exc)
        items = list_slow_tasks(limit)
        for it in items:
            it["source"] = "memory"
        return items


def clear_slow_tasks() -> None:
    with _lock:
        _events.clear()
