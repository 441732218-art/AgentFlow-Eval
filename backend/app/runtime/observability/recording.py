# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Helpers for recording runtime observation events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.runtime.events.models import RuntimeEvent as PublisherRuntimeEvent
from app.runtime.observability.events import RuntimeEvent

if TYPE_CHECKING:
    from app.runtime.correlation.models import CorrelationContext
    from app.runtime.executor.execution_context import ExecutionContext

logger = logging.getLogger(__name__)


def build_runtime_event(
    execution_context: ExecutionContext | None,
    event_type: str,
    *,
    tool_name: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
    correlation: CorrelationContext | None = None,
) -> RuntimeEvent:
    """Build a ``RuntimeEvent`` from execution context fields."""
    return RuntimeEvent(
        event_type=event_type,
        timestamp=timestamp or datetime.now(timezone.utc),
        execution_id=execution_context.execution_id if execution_context else "",
        agent_id=execution_context.agent_id if execution_context else None,
        tenant_id=execution_context.tenant_id if execution_context else None,
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        metadata=dict(metadata or {}),
        correlation_id=correlation.correlation_id if correlation else None,
        parent_event_id=correlation.parent_id if correlation else None,
        span_id=correlation.span_id if correlation else None,
    )


def _to_publisher_event(event: RuntimeEvent) -> PublisherRuntimeEvent:
    payload: dict[str, Any] = dict(event.metadata)
    if event.tool_name is not None:
        payload["tool_name"] = event.tool_name
    if event.status is not None:
        payload["status"] = event.status
    if event.duration_ms is not None:
        payload["duration_ms"] = event.duration_ms
    if event.correlation_id is not None:
        payload["correlation_id"] = event.correlation_id
    if event.parent_event_id is not None:
        payload["parent_event_id"] = event.parent_event_id
    if event.span_id is not None:
        payload["span_id"] = event.span_id
    return PublisherRuntimeEvent(
        event_type=event.event_type,
        execution_id=event.execution_id,
        agent_id=event.agent_id,
        tenant_id=event.tenant_id,
        timestamp=event.timestamp,
        payload=payload,
    )


def record_runtime_event(
    execution_context: ExecutionContext | None,
    event: RuntimeEvent,
) -> None:
    """Record and optionally publish ``event``; never interrupt execution."""
    if execution_context is None:
        return

    collector = execution_context.observation_collector
    if collector is not None:
        try:
            collector.record(event)
        except Exception:
            logger.debug("runtime observation record failed", exc_info=True)

    publisher = execution_context.event_publisher
    if publisher is not None:
        try:
            publisher.publish(_to_publisher_event(event))
        except Exception:
            logger.debug("runtime event publish failed", exc_info=True)
