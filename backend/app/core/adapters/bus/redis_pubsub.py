# (c) 2026 AgentFlow-Eval
"""Redis pub/sub EventBusPort — delegates to existing events.publish path."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisEventBus:
    @property
    def backend_name(self) -> str:
        return "redis"

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        # Prefer existing task-event publisher when channel matches
        try:
            from app.core import events as ev

            if channel in (ev.CHANNEL, "agentflow:task_events") and payload.get("type"):
                ev.publish_task_event(payload)
                return
        except Exception as exc:
            logger.debug("delegated publish_task_event failed: %s", exc)

        # Generic channel publish (best-effort Redis)
        try:
            import json
            import redis as sync_redis
            from app.config import settings

            body = json.dumps(payload, ensure_ascii=False, default=str)
            client = sync_redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
            try:
                client.publish(channel, body)
            finally:
                client.close()
        except Exception as exc:
            logger.debug("RedisEventBus publish skipped: %s", exc)
