# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution step helpers for agent pipelines."""

from __future__ import annotations

from typing import Any

from app.runtime.pipeline.models import ExecutionStep


def create_step(
    name: str,
    step_type: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> ExecutionStep:
    """Create a new running execution step."""
    return ExecutionStep(
        name=name,
        step_type=step_type,
        status="RUNNING",
        metadata=dict(metadata or {}),
    )


def complete_step(step: ExecutionStep) -> ExecutionStep:
    """Mark an execution step as completed."""
    step.status = "COMPLETED"
    return step


def fail_step(step: ExecutionStep, error: BaseException | str | None = None) -> ExecutionStep:
    """Mark an execution step as failed."""
    step.status = "FAILED"
    if error is not None:
        if isinstance(error, BaseException):
            step.metadata["error_type"] = type(error).__name__
            step.metadata["error_message"] = str(error)
        else:
            step.metadata["error_message"] = error
    return step
