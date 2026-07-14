# (c) 2026 AgentFlow-Eval
"""WebSocket connection hub + Redis subscriber for live task events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

from app.core.events import CHANNEL, register_local_listener, unregister_local_listener

logger = logging.getLogger(__name__)


class ConnectionManager:
    """In-memory WebSocket fan-out."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("WS client connected (%d total)", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        logger.info("WS client disconnected (%d total)", len(self._clients))

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead: list[WebSocket] = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self._clients)


manager = ConnectionManager()

_subscriber_task: asyncio.Task | None = None


async def _on_local_event(event: dict[str, Any]) -> None:
    await manager.broadcast(event)


async def _redis_subscriber_loop() -> None:
    """Subscribe to Redis channel and rebroadcast to local WS clients."""
    while True:
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe(CHANNEL)
            logger.info("Redis subscriber listening on %s", CHANNEL)
            async for msg in pubsub.listen():
                if msg is None:
                    continue
                if msg.get("type") != "message":
                    continue
                raw = msg.get("data")
                if raw is None:
                    continue
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await manager.broadcast(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Back off harder so local/dev without Redis stays quiet
            logger.warning("Redis subscriber error, retry in 30s: %s", exc)
            await asyncio.sleep(30)


async def start_ws_hub() -> None:
    global _subscriber_task
    register_local_listener(_on_local_event)

    from app.config import settings

    # Eager / no-worker local mode: in-process listeners only (no Redis retry spam)
    if settings.CELERY_TASK_ALWAYS_EAGER:
        logger.info("WS hub started (local events only, Redis subscriber skipped)")
        return

    if _subscriber_task is None or _subscriber_task.done():
        _subscriber_task = asyncio.create_task(_redis_subscriber_loop())
        logger.info("WS hub started (Redis pub/sub enabled)")


async def stop_ws_hub() -> None:
    global _subscriber_task
    unregister_local_listener(_on_local_event)
    if _subscriber_task and not _subscriber_task.done():
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
    _subscriber_task = None
    logger.info("WS hub stopped")
