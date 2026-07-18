# (c) 2026 AgentFlow-Eval
"""指标计算工具函数 —— 提供无 LLM 调用的轻量级辅助评分。"""

import re
from typing import Any


def calc_tool_accuracy(
    actual_tool_names: list[str],
    expected_tools: list[str],
) -> tuple[float, str]:
    """计算工具调用准确率（0-100）。

    基于集合的精确匹配和召回率计算。

    Args:
        actual_tool_names: 实际调用的工具名称列表。
        expected_tools: 期望调用的工具名称列表。

    Returns:
        (score, reason): 分数（0-100）和说明文字。
    """
    actual_set = set(actual_tool_names)
    expected_set = set(expected_tools)

    if not expected_set:
        return 100.0, "无预期工具要求，默认满分。"

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    penalty = 0.0
    reasons = []

    if missing:
        penalty += len(missing) * 10.0
        reasons.append(f"缺少工具: {', '.join(sorted(missing))}")
    if extra:
        penalty += len(extra) * 10.0
        reasons.append(f"多余工具: {', '.join(sorted(extra))}")

    score = max(0.0, 100.0 - penalty)
    reason = "; ".join(reasons) if reasons else "全部预期工具均已调用，无多余调用。"

    return score, reason


def extract_answer_text(steps: list[dict[str, Any]]) -> str:
    """从 ReAct 步骤数组中提取最终的答案文本。

    遍历步骤，取最后一个 role='assistant' 的内容作为最终答案。

    Args:
        steps: ReAct 步骤数组。

    Returns:
        最终答案文本，未找到时返回空字符串。
    """
    for step in reversed(steps):
        if step.get("role") == "assistant":
            content = step.get("content", "")
            if content:
                return content
        # 某些格式使用 type='final_answer'
        if step.get("type") == "final_answer":
            return step.get("content", "")
    return ""


def _normalize(text: str) -> str:
    """归一化文本用于模糊比较。"""
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text)
