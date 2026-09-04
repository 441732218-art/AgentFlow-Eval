# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Policy execution binding interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.policy_binding.models import PolicyBindingRequest, PolicyBindingResult


class PolicyExecutionBinder(Protocol):
    """Binds governance policy versions to runtime executions."""

    def bind(self, request: PolicyBindingRequest) -> PolicyBindingResult:
        """Bind one policy version to an execution observation record."""
