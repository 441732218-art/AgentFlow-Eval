# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Basic run state. Not Memory. Not RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    """Per-run bag. Holds input/output for this invocation only."""

    input: Any = None
    output: Any = None
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    steps: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def apply_pipeline_result(self, result: dict[str, Any]) -> None:
        """Copy fields from a v1 ``ensure_pipeline_result`` dict (no DB write)."""
        self.steps = list(result.get("steps") or [])
        self.output = result.get("final_answer")
        if self.output is None:
            self.output = result.get("output")
        self.status = str(result.get("status") or self.status)
        extra = dict(self.extra)
        extra["total_tokens"] = int(result.get("total_tokens") or 0)
        extra["response_time_ms"] = int(result.get("response_time_ms") or 0)
        extra["error_message"] = str(result.get("error_message") or "")
        extra["iterations"] = int(result.get("iterations") or 0)
        extra["runner"] = str(result.get("runner") or "")
        self.extra = extra
