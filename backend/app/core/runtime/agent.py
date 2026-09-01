# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""In-memory Agent entity. No database in Sprint 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Agent:
    """First-class Agent identity for Runtime (not a v1 Task).

    Fields are intentionally minimal. ``config`` is the same shape as v1
    ``Task.agent_config`` so Step 4 adapters can pass it to
    ``build_agent_runner`` unchanged.
    """

    agent_id: str
    name: str
    runner_type: str
    config: dict[str, Any] = field(default_factory=dict)
