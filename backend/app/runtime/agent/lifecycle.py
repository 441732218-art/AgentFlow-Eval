# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent session lifecycle helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.session import ExecutionSession
from app.runtime.observability.events import RuntimeEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext


def start_session(
    agent_definition: AgentDefinition,
    execution_context: ExecutionContext,
    *,
    task: str,
    tenant_id: str | None = None,
    user_id: str | None = None,
    execution_id: str | None = None,
) -> ExecutionSession:
    """Create a running session and publish ``agent.started``."""
    resolved_execution_id = execution_id or execution_context.execution_id or uuid.uuid4().hex
    started_at = datetime.now(timezone.utc)
    session = ExecutionSession(
        execution_id=resolved_execution_id,
        agent_id=agent_definition.id,
        tenant_id=tenant_id or execution_context.tenant_id,
        user_id=user_id or execution_context.user_id,
        status="RUNNING",
        started_at=started_at,
    )
    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            RuntimeEventType.AGENT_STARTED,
            status="running",
            metadata={
                "agent_name": agent_definition.name,
                "tool_names": list(agent_definition.tool_names),
                "task": task,
            },
        ),
    )
    return session


def complete_session(
    session: ExecutionSession,
    execution_context: ExecutionContext,
    *,
    agent_definition: AgentDefinition,
    output: object | None = None,
) -> ExecutionSession:
    """Mark a session completed and publish ``agent.completed``."""
    session.status = "COMPLETED"
    session.finished_at = datetime.now(timezone.utc)
    duration_ms = None
    if session.started_at is not None:
        duration_ms = max(
            0.0,
            (session.finished_at - session.started_at).total_seconds() * 1000,
        )
    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            RuntimeEventType.AGENT_COMPLETED,
            status="completed",
            duration_ms=duration_ms,
            metadata={
                "agent_name": agent_definition.name,
                "output_type": type(output).__name__ if output is not None else "none",
            },
        ),
    )
    return session


def fail_session(
    session: ExecutionSession,
    execution_context: ExecutionContext,
    *,
    agent_definition: AgentDefinition,
    error: BaseException | str,
) -> ExecutionSession:
    """Mark a session failed and publish ``agent.failed``."""
    session.status = "FAILED"
    session.finished_at = datetime.now(timezone.utc)
    error_type = type(error).__name__ if isinstance(error, BaseException) else "RuntimeError"
    error_message = str(error)
    duration_ms = None
    if session.started_at is not None and session.finished_at is not None:
        duration_ms = max(
            0.0,
            (session.finished_at - session.started_at).total_seconds() * 1000,
        )
    record_runtime_event(
        execution_context,
        build_runtime_event(
            execution_context,
            RuntimeEventType.AGENT_FAILED,
            status="failed",
            duration_ms=duration_ms,
            metadata={
                "agent_name": agent_definition.name,
                "error_type": error_type,
                "error_message": error_message,
            },
        ),
    )
    return session
