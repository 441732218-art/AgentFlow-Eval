# -*- coding: utf-8 -*-
"""
修复 source_code_60pages.txt:
  1. 补全 registry.py 缺失的尾部方法
  2. 为 billing 代码段补上文件头 + 版权头
  3. 补全被截断的方法签名
"""
from pathlib import Path

SRC = Path("copyright_output/source_code_60pages.txt")
lines = SRC.read_text(encoding="utf-8").split("\n")

# ── 定位截断行 ──────────────────────────────────────────
fix_idx = None
for i, ln in enumerate(lines):
    if ln.strip().startswith("self, features: dict[str, Any]"):
        prev = lines[i - 1].strip() if i > 0 else ""
        if not prev.endswith("("):          # 前一行不是正常的参数续行
            fix_idx = i
            break

if fix_idx is None:
    print("[SKIP] 未找到截断位置，文件可能已修复。")
else:
    # ── 1. registry.py 缺失的尾部 ──────────────────────
    registry_tail = """\

    def unregister_tools(self, plugin_id: str) -> int:
        \"\"\"移除指定插件注册的所有工具，返回移除数量。\"\"\"
        removed = 0
        for name in list(self._tools.keys()):
            if self._tools[name].get("plugin_id") == plugin_id:
                del self._tools[name]
                removed += 1
        return removed

    def get_tool(self, name: str) -> dict[str, Any] | None:
        \"\"\"按名称查找已注册工具。\"\"\"
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        \"\"\"列出所有已注册工具的元信息。\"\"\"
        return list(self._tools.values())


_registry: PluginCapabilityRegistry | None = None


def get_capability_registry() -> PluginCapabilityRegistry:
    \"\"\"获取全局插件能力注册表单例。\"\"\"
    global _registry
    if _registry is None:
        _registry = PluginCapabilityRegistry()
    return _registry


def reset_capability_registry() -> None:
    \"\"\"重置全局注册表（仅用于测试）。\"\"\"
    global _registry
    _registry = None
""".split("\n")

    # ── 2. billing.py 文件头 + 缺失的类定义 ────────────
    billing_head = """\
#=== File: backend/app/core/billing.py ===
# AgentFlow-Eval Agent自动化评测工作台 V1.0 | Author: LiKaixin
#====================================================================
# AgentFlow-Eval Agent自动化评测工作台 V1.0
\"\"\"计费与配额管理服务。\"\"\"
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QuotaBalance:
    \"\"\"租户配额余额快照。\"\"\"
    tenant_id: str
    period: str
    credits_total: int = 0
    credits_used: int = 0
    rollover_credits: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def credits_remaining(self) -> int:
        return max(0, self.credits_total + self.rollover_credits - self.credits_used)


class BillingService:
    \"\"\"处理配额查询、扣减与周期结转。\"\"\"

    def __init__(self, *, default_quota: int = 10_000) -> None:
        self._default_quota = default_quota
        self._balances: dict[str, QuotaBalance] = {}

    async def get_balance(self, session: Any, tenant_id: str) -> QuotaBalance:
        \"\"\"获取租户当前周期的配额余额。\"\"\"
        if tenant_id not in self._balances:
            self._balances[tenant_id] = QuotaBalance(
                tenant_id=tenant_id,
                period=datetime.now(timezone.utc).strftime("%Y-%m"),
                credits_total=self._default_quota,
            )
        return self._balances[tenant_id]

    async def deduct(self, session: Any, tenant_id: str, amount: int) -> QuotaBalance:
        \"\"\"扣减配额，余额不足时抛出 ValueError。\"\"\"
        bal = await self.get_balance(session, tenant_id)
        if bal.credits_remaining < amount:
            raise ValueError(f"Insufficient credits for tenant {tenant_id}")
        bal.credits_used += amount
        bal.updated_at = datetime.now(timezone.utc)
        return bal

    def _check_feature_access(
""".split("\n")

    # ── 3. 组装并写回 ──────────────────────────────────
    insert = registry_tail + [""] + billing_head
    new_lines = lines[:fix_idx] + insert + lines[fix_idx:]
    SRC.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"[OK] 已在第 {fix_idx + 1} 行前插入 {len(insert)} 行修复内容")
    print("     - registry.py 尾部方法已补全")
    print("     - billing.py 文件头 + 类定义已补全")
    print("     - 截断方法签名已修复")