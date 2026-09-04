# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime enforcement pipeline interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.enforcement_pipeline.models import (
    EnforcementRequest,
    EnforcementResult,
)


class RuntimeEnforcementPipeline(Protocol):
    """Evaluates gateway results through the runtime enforcement pipeline."""

    def evaluate(self, request: EnforcementRequest) -> EnforcementResult:
        """Evaluate one enforcement request and return an enforcement result."""
