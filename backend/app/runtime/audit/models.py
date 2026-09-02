# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Audit record model for enterprise runtime governance."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.runtime.events.event_types import RuntimeEventType

if TYPE_CHECKING:
    from app.runtime.events.models import RuntimeEvent


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit record with a JSON-safe payload."""

    id: str
    event_type: str
    execution_id: str
    timestamp: datetime
    agent_id: str | None = None
    tenant_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


def audit_record_from_runtime_event(event: RuntimeEvent) -> AuditRecord:
    """Convert a publishable runtime event into an audit record."""
    event_type = (
        event.event_type.value
        if isinstance(event.event_type, RuntimeEventType)
        else str(event.event_type)
    )
    return AuditRecord(
        id=uuid.uuid4().hex,
        event_type=event_type,
        execution_id=event.execution_id,
        agent_id=event.agent_id,
        tenant_id=event.tenant_id,
        timestamp=event.timestamp,
        payload=dict(event.payload),
    )
