# (c) 2026 AgentFlow-Eval
"""Task activity events — Redis pub/sub + local callback bridge for WebSocket.

Celery workers publish here; the API process subscribes and fans out to WS clients.
When Redis is unavailable, in-process listeners still receive local publishes.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

CHANNEL = "agentflow:task_events"

# Local async listeners (API process only)
_local_listeners: list[Callable[[dict[str, Any]], Awaitable[None]]] = []


def register_local_listener(cb: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    if cb not in _local_listeners:
        _local_listeners.append(cb)


def unregister_local_listener(cb: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    if cb in _local_listeners:
        _local_listeners.remove(cb)


def build_task_event(
    *,
    task_id: str,
    task_name: str,
    status: str,
    prev_status: str | None = None,
    actor: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "task_status",
        "task_id": task_id,
        "task_name": task_name,
        "status": status,
        "prev_status": prev_status,
        "actor": actor or "anonymous",
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload["extra"] = extra
    return payload


def publish_task_event(event: dict[str, Any]) -> None:
    """Sync-safe publish for Celery workers and FastAPI endpoints.

    1) Publish to Redis (best-effort)
    2) Schedule local async listeners if a loop is running
    """
    body = json.dumps(event, ensure_ascii=False, default=str)

    # Redis fan-out (works across processes)
    try:
        import redis as sync_redis
        from app.config import settings

        client = sync_redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
        try:
            client.publish(CHANNEL, body)
        finally:
            client.close()
    except Exception as exc:
        logger.debug("Redis publish skipped: %s", exc)

    # In-process async listeners (API only)
    try:
        import asyncio

        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    for cb in list(_local_listeners):
        try:
            loop.create_task(cb(event))
        except Exception as exc:
            logger.debug("Local listener schedule failed: %s", exc)


def publish_task_status(
    task_id: str,
    task_name: str,
    status: str,
    *,
    prev_status: str | None = None,
    actor: str | None = None,
) -> None:
    publish_task_event(
        build_task_event(
            task_id=task_id,
            task_name=task_name,
            status=status if isinstance(status, str) else str(status),
            prev_status=prev_status,
            actor=actor,
        )
    )
