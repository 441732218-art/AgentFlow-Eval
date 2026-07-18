# (c) 2026 AgentFlow-Eval
"""Best-effort DB sink for agent_logs (thread-safe queue + sync flush).

No background thread (avoids races with Celery/tests). Flush when:
- queue reaches LOG_DB_BATCH_SIZE
- explicit flush_agent_logs_sync() (API list / atexit)
"""

from __future__ import annotations

import atexit
import logging
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("app.aols.sink")

_queue: deque[dict[str, Any]] = deque(maxlen=5000)
_lock = threading.Lock()


def _settings_enabled() -> bool:
    try:
        from app.config import settings

        return bool(getattr(settings, "LOG_DB_SINK", True))
    except Exception:
        return True


def _batch_size() -> int:
    try:
        from app.config import settings

        return max(1, int(getattr(settings, "LOG_DB_BATCH_SIZE", 32) or 32))
    except Exception:
        return 32


def enqueue_agent_log(
    *,
    event: str,
    level: str = "info",
    service: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Non-blocking enqueue. Never raises."""
    if not _settings_enabled():
        return
    try:
        from app.config import settings

        svc = service or getattr(settings, "LOG_SERVICE_NAME", "agentflow-api")
    except Exception:
        svc = service or "agentflow-api"

    row = {
        "id": str(uuid.uuid4()),
        "level": (level or "info")[:16],
        "event": (event or "unknown")[:96],
        "service": (svc or "agentflow-api")[:64],
        "trace_id": (str(trace_id)[:64] if trace_id else None),
        "task_id": (str(task_id)[:64] if task_id else None),
        "payload": dict(payload or {}),
        "created_at": datetime.now(timezone.utc),
    }
    try:
        should_flush = False
        with _lock:
            _queue.append(row)
            should_flush = len(_queue) >= _batch_size()
        if should_flush:
            flush_agent_logs_sync()
    except Exception as exc:
        logger.debug("enqueue_agent_log skipped: %s", exc)


def flush_agent_logs_sync(limit: int | None = None) -> int:
    """Drain up to *limit* rows into DB. Returns written count. Never raises."""
    if not _settings_enabled():
        return 0
    n = limit or _batch_size() * 4
    batch: list[dict[str, Any]] = []
    try:
        with _lock:
            while _queue and len(batch) < n:
                batch.append(_queue.popleft())
    except Exception:
        return 0
    if not batch:
        return 0

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.config import settings
        from app.models.agent_log import AgentLog

        url = settings.DATABASE_URL
        sync_url = (
            url.replace("sqlite+aiosqlite://", "sqlite://")
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgres+asyncpg://", "postgresql://")
        )
        engine = create_engine(sync_url, pool_pre_ping=True)
        written = 0
        try:
            with Session(engine) as session:
                for row in batch:
                    session.add(
                        AgentLog(
                            id=row["id"],
                            level=row["level"],
                            event=row["event"],
                            service=row["service"],
                            trace_id=row.get("trace_id"),
                            task_id=row.get("task_id"),
                            payload=row.get("payload") or {},
                        )
                    )
                    written += 1
                session.commit()
        finally:
            engine.dispose()
        return written
    except Exception as exc:
        logger.debug("flush_agent_logs_sync failed (%d rows): %s", len(batch), exc)
        return 0


def reset_sink_for_tests() -> None:
    """Clear in-memory queue (unit tests)."""
    with _lock:
        _queue.clear()


def _atexit_flush() -> None:
    try:
        flush_agent_logs_sync(limit=500)
    except Exception:
        pass


atexit.register(_atexit_flush)
