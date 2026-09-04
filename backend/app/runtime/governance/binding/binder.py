# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime enforcement binding interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.binding.models import RuntimeBindingRequest, RuntimeBindingResult


class RuntimeEnforcementBinder(Protocol):
    """Binds enforcement results to runtime observation records."""

    def bind(self, request: RuntimeBindingRequest) -> RuntimeBindingResult:
        """Bind one enforcement result and return a binding result."""
