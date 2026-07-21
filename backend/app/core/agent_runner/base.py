# (c) 2026 AgentFlow-Eval
"""Agent runner abstract base — unified run() contract (Phase 0).

All runners (OpenAI ReAct, HTTP, plugins) share the same call shape so the
Celery pipeline never needs TypeError dual-paths:

    await runner.run(query, tools=..., agent_config=...)

Return either a pipeline ``dict`` or :class:`AgentResult` (auto-normalized).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentResult:
    """Normalized agent execution result.

    Prefer :meth:`to_pipeline_dict` when persisting Trace rows. Extra keys
    (e.g. ``final_answer``, ``runner``) may be present for richer runners.
    """

    steps: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    response_time_ms: int = 0
    status: str = "success"
    error_message: str = ""
    finished_at: datetime | None = None
    final_answer: str = ""
    iterations: int = 0
    runner: str = ""

    def to_pipeline_dict(self) -> dict[str, Any]:
        """Convert to the dict shape expected by Trace persistence."""
        data = asdict(self)
        # Drop None finished_at noise; keep status fields always.
        if data.get("finished_at") is not None and hasattr(
            data["finished_at"], "isoformat"
        ):
            data["finished_at"] = data["finished_at"].isoformat()
        return data


def ensure_pipeline_result(result: AgentResult | dict[str, Any] | Any) -> dict[str, Any]:
    """Normalize any runner return value into a pipeline-compatible dict.

    Args:
        result: AgentResult, plain dict, or object with attributes.

    Returns:
        Dict with at least ``steps``, ``status``, ``total_tokens``,
        ``response_time_ms``, ``error_message``.
    """
    if isinstance(result, AgentResult):
        return result.to_pipeline_dict()
    if isinstance(result, dict):
        out = dict(result)
        out.setdefault("steps", [])
        out.setdefault("total_tokens", 0)
        out.setdefault("response_time_ms", 0)
        out.setdefault("status", "success")
        out.setdefault("error_message", "")
        return out
    # Duck-typed fallback (tests / legacy objects)
    return {
        "steps": list(getattr(result, "steps", None) or []),
        "total_tokens": int(getattr(result, "total_tokens", 0) or 0),
        "response_time_ms": int(getattr(result, "response_time_ms", 0) or 0),
        "status": str(getattr(result, "status", "success") or "success"),
        "error_message": str(getattr(result, "error_message", "") or ""),
        "final_answer": str(getattr(result, "final_answer", "") or ""),
        "iterations": int(getattr(result, "iterations", 0) or 0),
        "runner": str(getattr(result, "runner", "") or ""),
    }


class BaseAgentRunner(ABC):
    """Agent executor abstract base.

    Implementations must provide :meth:`run` with the unified signature below.
    Returning either ``dict`` or :class:`AgentResult` is accepted; the pipeline
    always normalizes via :func:`ensure_pipeline_result`.
    """

    @abstractmethod
    async def run(
        self,
        query: str,
        tools: list[Any] | None = None,
        *,
        agent_config: dict[str, Any] | None = None,
    ) -> AgentResult | dict[str, Any]:
        """Execute one agent invocation.

        Args:
            query: User / suite query string.
            tools: Optional tool definitions (OpenAI-style dicts) or name list.
            agent_config: Full task-level agent_config (model, endpoint, etc.).

        Returns:
            Pipeline dict or AgentResult.
        """
        raise NotImplementedError
