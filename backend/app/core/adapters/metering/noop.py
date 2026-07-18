# (c) 2026 AgentFlow-Eval
"""No-op metering (billing disabled / lite / private default)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NoopMeter:
    @property
    def backend_name(self) -> str:
        return "noop"

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
        logger.debug(
            "meter.noop actor=%s metric=%s qty=%s ref=%s/%s",
            actor,
            metric,
            quantity,
            ref_type,
            ref_id,
        )
