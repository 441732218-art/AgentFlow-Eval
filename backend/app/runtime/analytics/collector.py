# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime analytics collection coordinator."""

from __future__ import annotations

from app.runtime.analytics.models import ExecutionMetric, StepMetric, ToolMetric
from app.runtime.analytics.store import AnalyticsStore


class RuntimeAnalyticsCollector:
    """Collect runtime execution analytics and persist them via an analytics store."""

    def __init__(self, store: AnalyticsStore) -> None:
        self._store = store

    @property
    def store(self) -> AnalyticsStore:
        return self._store

    def collect_execution_metric(self, metric: ExecutionMetric) -> None:
        """Persist an execution-level analytics metric."""
        self._store.save_execution_metric(metric)

    def collect_step_metric(self, metric: StepMetric) -> None:
        """Persist a step-level analytics metric."""
        self._store.save_step_metric(metric)

    def collect_tool_metric(self, metric: ToolMetric) -> None:
        """Persist a tool-level analytics metric."""
        self._store.save_tool_metric(metric)
