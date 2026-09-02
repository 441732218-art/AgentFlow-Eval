# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent execution pipeline models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PipelineStatus = Literal["RUNNING", "COMPLETED", "FAILED"]

StepStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


@dataclass
class ExecutionStep:
    """Single step in an agent execution pipeline."""

    name: str
    step_type: str
    status: StepStatus = "PENDING"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecutionResult:
    """Structured outcome of an agent execution pipeline run."""

    execution_id: str
    agent_id: str
    status: PipelineStatus
    output: Any | None = None
    steps: list[ExecutionStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
