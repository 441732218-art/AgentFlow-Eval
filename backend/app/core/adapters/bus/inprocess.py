# (c) 2026 AgentFlow-Eval
"""In-process event bus — local listeners only (lite profile)."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class InProcessEventBus:
    @property
    def backend_name(self) -> str:
        return "inprocess"

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        # Reuse existing local listener bridge without Redis
        try:
            from app.core.events import _local_listeners  # noqa: PLC2701
            import asyncio

            async def _fanout() -> None:
                for cb in list(_local_listeners):
                    try:
                        await cb(payload)
                    except Exception as exc:
                        logger.debug("local listener error: %s", exc)

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_fanout())
            except RuntimeError:
                # No loop — drop (sync worker without API process)
                logger.debug(
                    "InProcess publish skipped (no loop) channel=%s bytes=%s",
                    channel,
                    len(json.dumps(payload, default=str)),
                )
        except Exception as exc:
            logger.debug("InProcess publish failed: %s", exc)
