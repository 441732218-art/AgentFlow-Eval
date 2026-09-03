# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Failure policy abstraction for controlled step execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

FailureAction = Literal["STOP", "CONTINUE"]


@runtime_checkable
class FailurePolicy(Protocol):
    """Decides plan-level behavior after a step fails."""

    @property
    def action(self) -> FailureAction:
        """Plan-level action when a step exhausts retries."""

    def should_stop_plan(self) -> bool:
        """Return ``True`` when plan execution should halt on step failure."""


@dataclass(frozen=True)
class DefaultFailurePolicy:
    """Default failure policy stops plan execution on the first step failure."""

    action: FailureAction = "STOP"

    def should_stop_plan(self) -> bool:
        return self.action == "STOP"
