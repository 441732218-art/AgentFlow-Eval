# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Retry policy abstraction for controlled step execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class RetryPolicy(Protocol):
    """Decides whether a failed step attempt should be retried."""

    @property
    def max_attempts(self) -> int:
        """Maximum number of execution attempts for a single step."""

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Return ``True`` when another attempt is allowed after ``attempt`` failed."""


@dataclass(frozen=True)
class DefaultRetryPolicy:
    """Default retry policy; ``max_attempts=1`` means no retry."""

    max_attempts: int = 1

    def should_retry(self, attempt: int, error: Exception) -> bool:
        _ = error
        return attempt < self.max_attempts
