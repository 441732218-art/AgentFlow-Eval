# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime analytics persistence interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.analytics.models import ExecutionMetric, StepMetric, ToolMetric


class AnalyticsStore(Protocol):
    """Persists runtime execution analytics metrics."""

    def save_execution_metric(self, metric: ExecutionMetric) -> None:
        """Persist an execution-level metric."""

    def save_step_metric(self, metric: StepMetric) -> None:
        """Persist a step-level metric."""

    def save_tool_metric(self, metric: ToolMetric) -> None:
        """Persist a tool-level metric."""

    def get_execution_metrics(
        self,
        execution_id: str | None = None,
    ) -> list[ExecutionMetric]:
        """Return execution metrics, optionally filtered by execution id."""
