# (c) 2026 AgentFlow-Eval
"""成本计算工具 —— 基于模型和 Token 数量计算 API 调用费用。

用法:
    from app.utils.cost import calculate_cost
    cost = calculate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """每百万 Token 的价格（USD）。"""

    prompt_per_million: float
    completion_per_million: float


# 官方定价表 (截至 2025-Q2，请定期更新)
# https://openai.com/pricing
MODEL_PRICING: dict[str, ModelPricing] = {
    # GPT-4o 系列
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4o-2024-11-20": ModelPricing(2.50, 10.00),
    "gpt-4o-2024-08-06": ModelPricing(2.50, 10.00),
    "gpt-4o-2024-05-13": ModelPricing(5.00, 15.00),
    # GPT-4o-mini 系列
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "gpt-4o-mini-2024-07-18": ModelPricing(0.15, 0.60),
    # GPT-4.1 系列
    "gpt-4.1": ModelPricing(2.00, 8.00),
    "gpt-4.1-mini": ModelPricing(0.40, 1.60),
    "gpt-4.1-nano": ModelPricing(0.10, 0.40),
    # o 系列推理模型
    "o4-mini": ModelPricing(1.10, 4.40),
    "o3": ModelPricing(2.00, 8.00),
    "o3-mini": ModelPricing(1.10, 4.40),
    "o1": ModelPricing(15.00, 60.00),
    "o1-mini": ModelPricing(1.10, 4.40),
    # GPT-4 Turbo (legacy)
    "gpt-4-turbo": ModelPricing(10.00, 30.00),
    "gpt-4-turbo-preview": ModelPricing(10.00, 30.00),
    # GPT-3.5 (legacy)
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50),
    "gpt-3.5-turbo-0125": ModelPricing(0.50, 1.50),
}

# 默认 fallback 价格（使用 gpt-4o-mini 作为保守估算）
_DEFAULT_PRICING = ModelPricing(0.15, 0.60)


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """计算单次 API 调用的费用（USD）。

    Args:
        model: 模型名称（如 "gpt-4o-mini"）。
        prompt_tokens: 输入 Token 数。
        completion_tokens: 输出 Token 数。

    Returns:
        费用（USD），保留 8 位小数以支持微量计费。

    Examples:
        >>> calculate_cost("gpt-4o-mini", 1000, 500)
        0.00045
        >>> calculate_cost("gpt-4o", 10000, 5000)
        0.075
    """
    pricing = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    cost = (prompt_tokens / 1_000_000) * pricing.prompt_per_million + (
        completion_tokens / 1_000_000
    ) * pricing.completion_per_million
    return round(cost, 8)


def get_supported_models() -> list[str]:
    """返回所有已配置定价的模型列表。"""
    return sorted(MODEL_PRICING.keys())
