# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance report store."""

from __future__ import annotations

import threading

from app.runtime.governance.reporting.models import GovernanceReport


class InMemoryReportStore:
    """Thread-safe in-memory governance report store."""

    def __init__(self) -> None:
        self._reports: dict[str, GovernanceReport] = {}
        self._lock = threading.Lock()

    def create(self, report: GovernanceReport) -> None:
        with self._lock:
            self._reports[report.report_id] = report

    def get(self, report_id: str) -> GovernanceReport | None:
        with self._lock:
            return self._reports.get(report_id)

    def list_by_execution(self, execution_id: str) -> list[GovernanceReport]:
        with self._lock:
            reports = [
                report
                for report in self._reports.values()
                if report.execution_id == execution_id
            ]
        return sorted(reports, key=lambda report: report.created_at)

    def delete(self, report_id: str) -> None:
        with self._lock:
            self._reports.pop(report_id, None)
