# (c) 2026 AgentFlow-Eval
"""Agent Runner 抽象基类，统一 run() 契约。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentResult:
    """Runner 执行结果；落库时用 to_pipeline_dict()。"""

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
        """转成 Trace 落库用的 dict。"""
        data = asdict(self)
        # finished_at 转 iso 字符串
        if data.get("finished_at") is not None and hasattr(
            data["finished_at"], "isoformat"
        ):
            data["finished_at"] = data["finished_at"].isoformat()
        return data


def ensure_pipeline_result(result: AgentResult | dict[str, Any] | Any) -> dict[str, Any]:
    """Normalize runner output to a pipeline-compatible dict."""
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
    # 兼容旧对象/测试替身
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
    """子类实现 run()，返回 dict 或 AgentResult。"""

    @abstractmethod
    async def run(
        self,
        query: str,
        tools: list[Any] | None = None,
        *,
        agent_config: dict[str, Any] | None = None,
    ) -> AgentResult | dict[str, Any]:
        """Execute one agent invocation; return pipeline dict or AgentResult."""
        raise NotImplementedError
