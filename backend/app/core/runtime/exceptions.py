# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Runtime-specific exceptions. Isolated from v1 evaluation errors."""

from __future__ import annotations


class AgentRuntimeError(Exception):
    """Base error for the additive Agent Runtime package."""

    def __init__(self, message: str = "Runtime error") -> None:
        self.message = message
        super().__init__(message)


class AgentNotFoundError(AgentRuntimeError):
    """Raised when the in-memory registry has no agent for the given id."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent not found: {agent_id}")


class DuplicateAgentError(AgentRuntimeError):
    """Raised when register() is called with an existing agent_id."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent already registered: {agent_id}")


class AdapterNotConfiguredError(AgentRuntimeError):
    """Raised when Executor has no adapter resolver (wired in Step 4)."""

    def __init__(self, runner_type: str = "") -> None:
        self.runner_type = runner_type
        suffix = f" for runner_type={runner_type!r}" if runner_type else ""
        super().__init__(
            "No Runtime adapter configured"
            + suffix
            + ". Sprint 1 Step 4 will bind adapters via build_agent_runner."
        )


class RuntimeDisabledError(AgentRuntimeError):
    """Raised when ENABLE_RUNTIME_V2 is false (API layer, Step 5)."""

    def __init__(self) -> None:
        super().__init__("runtime_disabled")
        self.code = "runtime_disabled"
