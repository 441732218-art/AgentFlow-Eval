# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Service-layer DTOs for Runtime HTTP API adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.runtime.execution.models import ExecutionRecord


@dataclass
class ExecutionResponseDTO:
    """Public execution response for ``POST /runtime/execute``."""

    execution_id: str
    status: str
    output: Any | None
    error: str | None


@dataclass
class ExecutionQueryDTO:
    """Public execution query response for ``GET /runtime/executions/{id}``."""

    execution_id: str
    status: str
    output: Any | None
    error: str | None
    created_at: datetime
    updated_at: datetime


def execution_record_to_query_dto(record: ExecutionRecord) -> ExecutionQueryDTO:
    """Map a persisted record to the public query DTO (no trace/memory/tool fields)."""
    return ExecutionQueryDTO(
        execution_id=record.execution_id,
        status=record.status,
        output=record.output,
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
