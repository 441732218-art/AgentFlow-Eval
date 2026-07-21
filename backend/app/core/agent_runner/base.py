# (c) 2026 AgentFlow-Eval
"""Agent 执行器抽象基类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentResult:
    """Agent 执行结果数据类。"""

    steps: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    response_time_ms: int = 0
    status: str = "success"
    error_message: str = ""
    finished_at: datetime | None = None


class BaseAgentRunner(ABC):
    """Agent 执行器抽象基类。

    所有 Agent 实现（OpenAI、Claude 等）必须实现 run 方法，
    返回统一的 AgentResult 数据结构。
    """

    @abstractmethod
    async def run(
        self,
        user_query: str,
        agent_config: dict[str, Any],
    ) -> AgentResult:
        """执行一次 Agent 调用。

        Args:
            user_query: 用户输入指令。
            agent_config: Agent 配置参数（模型名称、温度等）。

        Returns:
            AgentResult: 包含执行步骤、Token 消耗和状态。
        """
        raise NotImplementedError
