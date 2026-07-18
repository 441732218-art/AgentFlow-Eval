# (c) 2026 AgentFlow-Eval
"""Agent 输出解析器 —— 从 Agent 响应中提取结构化信息。"""

from typing import Any


def parse_steps_from_response(response: str) -> list[dict[str, Any]]:
    """从 Agent 原始响应文本中解析 ReAct 步骤。

    作为 OpenAIRunner._parse_react_steps 的独立封装，
    可在需要轻量级解析的场景下直接使用。

    Args:
        response: Agent 返回的原始文本。

    Returns:
        结构化的步骤列表。
    """
    from app.core.agent_runner.openai_runner import OpenAIRunner
    return OpenAIRunner._parse_react_steps(response)
