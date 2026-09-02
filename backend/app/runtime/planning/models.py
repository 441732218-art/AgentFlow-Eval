# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.pipeline.models import ExecutionStep


@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable execution plan produced by a planner."""

    plan_id: str
    agent_id: str
    steps: tuple[ExecutionStep, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
