# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime execution analytics models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

MetricStatus = Literal["COMPLETED", "FAILED", "RUNNING"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ExecutionMetric:
    """Immutable aggregate metrics for one agent execution."""

    execution_id: str
    agent_id: str
    duration_ms: int
    status: MetricStatus
    step_count: int
    tool_count: int
    failure_count: int
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> ExecutionMetric:
        """Return a new metric with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


@dataclass(frozen=True)
class StepMetric:
    """Immutable metrics for one planned pipeline step."""

    execution_id: str
    step_id: str
    duration_ms: int
    status: MetricStatus
    error: str | None = None

    def with_updates(self, **changes: Any) -> StepMetric:
        """Return a new metric with updated fields."""
        return replace(self, **changes)


@dataclass(frozen=True)
class ToolMetric:
    """Immutable metrics for one tool invocation within an execution."""

    execution_id: str
    tool_name: str
    duration_ms: int
    status: MetricStatus
    error: str | None = None

    def with_updates(self, **changes: Any) -> ToolMetric:
        """Return a new metric with updated fields."""
        return replace(self, **changes)
