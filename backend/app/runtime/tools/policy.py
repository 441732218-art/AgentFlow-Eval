# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Remote execution policy — timeout and retry boundaries for providers."""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_ALLOWED_RETRIES = 5
DEFAULT_RETRYABLE_ERRORS = frozenset({"RemoteTimeoutError", "timeout"})


@dataclass
class RemoteExecutionPolicy:
    """Production-safe defaults for remote tool execution."""

    timeout_seconds: float = 30.0
    max_retries: int = 2
    retryable_errors: frozenset[str] = field(default_factory=lambda: DEFAULT_RETRYABLE_ERRORS)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("RemoteExecutionPolicy.timeout_seconds must be > 0")
        if self.max_retries < 0:
            raise ValueError("RemoteExecutionPolicy.max_retries must be >= 0")
        if self.max_retries > MAX_ALLOWED_RETRIES:
            raise ValueError(
                f"RemoteExecutionPolicy.max_retries must be <= {MAX_ALLOWED_RETRIES}"
            )
        if not isinstance(self.retryable_errors, frozenset):
            object.__setattr__(self, "retryable_errors", frozenset(self.retryable_errors))

    def is_retryable(self, error: Exception) -> bool:
        """Return whether ``error`` qualifies for another attempt."""
        error_type = type(error).__name__
        if error_type in self.retryable_errors:
            return True
        message = str(error).lower()
        return any(marker.lower() in message for marker in self.retryable_errors)

    @property
    def max_attempts(self) -> int:
        """Total attempts including the first call."""
        return self.max_retries + 1
