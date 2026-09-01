# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution context for Runtime trace hooks (tool / LLM / cost / latency)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeContext:
    """Per-execution context passed through the Runtime pipeline."""

    execution_id: str
    agent_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
