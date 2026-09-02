# AgentFlow-Eval Agent自动化评测工作台 V1.0
"""Agent 配置脱敏入口。

统一复用 ``app.core.observability.aols.redaction.redact_mapping``：
  - 递归处理 dict / list / 嵌套 dict / list
  - 大小写不敏感，覆盖 api_key / token / authorization / secret / password 等敏感字段
  - 用于 Task 响应回显、缓存序列化与结构化日志，避免泄露密钥

本模块作为兼容入口保留，避免在调用方复制多套脱敏逻辑。
"""

from __future__ import annotations

from typing import Any

from app.core.observability.aols.redaction import redact_mapping


def mask_agent_config(agent_config: dict[str, Any] | None) -> dict[str, Any]:
    """返回脱敏后的 agent_config 副本（递归），敏感 key 值替换为 ``[REDACTED]``。"""
    return redact_mapping(agent_config)
