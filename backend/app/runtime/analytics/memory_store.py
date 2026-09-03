# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime analytics store."""

from __future__ import annotations

import threading

from app.runtime.analytics.models import ExecutionMetric, StepMetric, ToolMetric


class InMemoryAnalyticsStore:
    """Thread-safe in-memory analytics store."""

    def __init__(self) -> None:
        self._execution_metrics: list[ExecutionMetric] = []
        self._step_metrics: list[StepMetric] = []
        self._tool_metrics: list[ToolMetric] = []
        self._lock = threading.Lock()

    def save_execution_metric(self, metric: ExecutionMetric) -> None:
        with self._lock:
            self._execution_metrics.append(metric)

    def save_step_metric(self, metric: StepMetric) -> None:
        with self._lock:
            self._step_metrics.append(metric)

    def save_tool_metric(self, metric: ToolMetric) -> None:
        with self._lock:
            self._tool_metrics.append(metric)

    def get_execution_metrics(
        self,
        execution_id: str | None = None,
    ) -> list[ExecutionMetric]:
        with self._lock:
            records = list(self._execution_metrics)
        if execution_id is not None:
            return [record for record in records if record.execution_id == execution_id]
        return records

    def get_step_metrics(
        self,
        execution_id: str | None = None,
    ) -> list[StepMetric]:
        with self._lock:
            records = list(self._step_metrics)
        if execution_id is not None:
            return [record for record in records if record.execution_id == execution_id]
        return records

    def get_tool_metrics(
        self,
        execution_id: str | None = None,
    ) -> list[ToolMetric]:
        with self._lock:
            records = list(self._tool_metrics)
        if execution_id is not None:
            return [record for record in records if record.execution_id == execution_id]
        return records

    def clear(self) -> None:
        with self._lock:
            self._execution_metrics.clear()
            self._step_metrics.clear()
            self._tool_metrics.clear()
