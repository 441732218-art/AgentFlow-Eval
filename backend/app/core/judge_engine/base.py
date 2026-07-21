# (c) 2026 AgentFlow-Eval
"""打分引擎抽象基类 —— 定义 evaluate 接口契约。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeResult:
    """评分结果数据类。"""

    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    reason: str = ""
    token_cost: int = 0


class BaseJudge(ABC):
    """打分引擎抽象基类。

    所有打分引擎实现必须实现 evaluate 方法。
    """

    @abstractmethod
    async def evaluate(
        self,
        trace_steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
    ) -> JudgeResult:
        """对一次执行轨迹进行多维度评分。

        Args:
            trace_steps: Agent 执行过程中的 ReAct 步骤数组。
            expected_output: 期望输出文本。
            expected_tools: 期望调用的工具名称列表。

        Returns:
            JudgeResult: 包含各维度分数、总分和扣分说明。
        """
        raise NotImplementedError
