# -*- coding: utf-8 -*-
"""
fix_source_v2.py  —  第二轮修复
解决问题：
  1. registry.py 尾部 + billing.py 文件头 重复出现两次
  2. _check_feature_access 签名断裂
  3. registry.py 类型标注错误 (.get("plugin_id") → .source_plugin)
  4. billing.py 两套实现矛盾 → 统一为 ORM 版
  5. 补全 billing.py 缺失的 import
"""

import re, sys, pathlib

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
text = SRC.read_text(encoding="utf-8")
lines = text.split("\n")
print(f"[INFO] 读入 {len(lines)} 行")

# ──────────────────────────────────────────────
# STEP 1: 定位重复区域并删除第一份（截断版）
# ──────────────────────────────────────────────
# 第一份特征：孤立的 "def _check_feature_access(" 后面紧跟的不是参数，
# 而是 "def unregister_tools" 或 "def get_tool"
# 第二份特征：完整的 "def _check_feature_access(\n    self, features..."

# 找所有 "_check_feature_access" 出现位置
occurrences = [i for i, ln in enumerate(lines) if "_check_feature_access" in ln]
print(f"[INFO] _check_feature_access 出现 {len(occurrences)} 次，行号: {occurrences}")

if len(occurrences) >= 2:
    # 第一处是截断版，需要删除从它开始到第二处之前的所有行
    first = occurrences[0]
    second = occurrences[1]

    # 向上找到第一份重复区域的起点：
    # 从 first 往上找，直到遇到上一个正常代码行（不属于重复块）
    # 重复块起点标志：第一次出现的 "def unregister_tools" 或孤立的 "def _check_feature_access("
    block_start = first
    # 往上扫描，如果上面紧挨着的是 registry 尾部方法（也是重复的），一并删除
    for i in range(first - 1, max(first - 120, 0), -1):
        stripped = lines[i].strip()
        if stripped.startswith("def unregister_tools") or \
           stripped.startswith("def get_tool") or \
           stripped.startswith("def list_tools") or \
           stripped.startswith("def get_capability_registry") or \
           stripped.startswith("def reset_capability_registry") or \
           stripped.startswith("_registry") or \
           stripped.startswith("#=== File: backend/app/core/billing.py") or \
           stripped.startswith("# Copyright") or \
           stripped.startswith('"""') or \
           stripped.startswith("from ") or \
           stripped.startswith("import ") or \
           stripped.startswith("class ") or \
           stripped.startswith("@dataclass") or \
           stripped.startswith("def ") or \
           stripped.startswith("self.") or \
           stripped.startswith("return ") or \
           stripped.startswith("if ") or \
           stripped.startswith("for ") or \
           stripped.startswith("now") or \
           stripped.startswith("balance") or \
           stripped.startswith("used") or \
           stripped.startswith("remaining") or \
           stripped.startswith("key") or \
           stripped.startswith("row") or \
           stripped.startswith("result") or \
           stripped.startswith("session") or \
           stripped.startswith("sub") or \
           stripped.startswith("logger") or \
           stripped.startswith("pk") or \
           stripped.startswith("period") or \
           stripped == "" or \
           stripped.startswith("#") or \
           stripped.startswith(")") or \
           stripped.startswith("(") or \
           stripped.startswith("]") or \
           stripped.startswith("[") or \
           stripped.startswith("}") or \
           stripped.startswith("{") or \
           stripped.startswith('"') or \
           stripped.startswith("'"):
            block_start = i
        else:
            break

    # 第二份的起点：往上找到它所属的 registry 尾部方法开头
    block2_start = second
    for i in range(second - 1, max(second - 120, 0), -1):
        stripped = lines[i].strip()
        if stripped.startswith("def unregister_tools"):
            block2_start = i
            break

    print(f"[INFO] 删除第一份重复区域: 行 {block_start+1} ~ {block2_start} (共 {block2_start - block_start} 行)")
    del lines[block_start:block2_start]
    print(f"[OK] 删除后剩余 {len(lines)} 行")
else:
    print("[WARN] 未发现重复，跳过 STEP 1")

# ──────────────────────────────────────────────
# STEP 2: 修复 registry.py 类型标注
# ──────────────────────────────────────────────
text = "\n".join(lines)

# 2a. unregister_tools 中 .get("plugin_id") → .source_plugin
text = text.replace(
    'if self._tools[name].get("plugin_id") == plugin_id:',
    'if self._tools[name].source_plugin == plugin_id:'
)
# 也处理单引号版本
text = text.replace(
    "if self._tools[name].get('plugin_id') == plugin_id:",
    "if self._tools[name].source_plugin == plugin_id:"
)

# 2b. get_tool 返回类型
text = text.replace(
    "def get_tool(self, name: str) -> dict[str, Any] | None:",
    "def get_tool(self, name: str) -> ToolSpec | None:"
)

# 2c. list_tools 返回类型
text = text.replace(
    "def list_tools(self) -> list[dict[str, Any]]:",
    "def list_tools(self) -> list[ToolSpec]:"
)

print("[OK] registry.py 类型标注已修复")

# ──────────────────────────────────────────────
# STEP 3: 统一 billing.py 为 ORM 版，补全 import
# ──────────────────────────────────────────────

# 找到 billing.py 文件头
billing_hdr = "#=== File: backend/app/core/billing.py ==="
billing_idx = text.find(billing_hdr)
if billing_idx == -1:
    print("[ERROR] 未找到 billing.py 文件头！")
    sys.exit(1)

# 找到下一个文件头（billing.py 的结束位置）
next_file_pattern = re.compile(r"\n#=== File: ")
m = next_file_pattern.search(text, billing_idx + len(billing_hdr))
billing_end = m.start() if m else len(text)
billing_block = text[billing_idx:billing_end]

# 检查是否存在内存版残留（self._balances）
if "self._balances" in billing_block:
    print("[INFO] 检测到内存版残留，重写 billing.py 为纯 ORM 版...")

    new_billing = '''#=== File: backend/app/core/billing.py ===
# Copyright (c) 2026 AgentFlow-Eval
# Author: LiKaixin
"""
billing.py - 租户配额与计费服务（ORM 版）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.core.tenancy import period_key

logger = logging.getLogger(__name__)


@dataclass
class QuotaBalance:
    """租户配额余额快照."""

    tenant_id: str
    credits_total: int = 0
    credits_used: int = 0
    token_used: int = 0
    token_limit: int = 100_000
    task_used: int = 0
    task_limit: int = 50
    storage_used_mb: float = 0.0
    storage_limit_mb: float = 1024.0
    plugin_used: int = 0
    plugin_limit: int = 5
    rollover_credits: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def credits_remaining(self) -> int:
        return max(0, self.credits_total + self.rollover_credits - self.credits_used)

    @property
    def token_remaining(self) -> int:
        return max(0, self.token_limit - self.token_used)

    @property
    def task_remaining(self) -> int:
        return max(0, self.task_limit - self.task_used)


class BillingService:
    """基于 ORM 的计费与配额管理服务."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def get_balance(self, tenant_id: str) -> QuotaBalance:
        """获取租户当前配额余额."""
        async with self._session_factory() as session:
            pk = period_key()
            result = await session.execute(
                select(Subscription).where(
                    Subscription.tenant_id == tenant_id,
                    Subscription.period == pk,
                )
            )
            sub = result.scalar_one_or_none()
            if sub is None:
                return QuotaBalance(tenant_id=tenant_id)
            return QuotaBalance(
                tenant_id=tenant_id,
                credits_total=sub.credits_total,
                credits_used=sub.credits_used,
                token_used=sub.token_used,
                token_limit=sub.token_limit,
                task_used=sub.task_used,
                task_limit=sub.task_limit,
                storage_used_mb=sub.storage_used_mb,
                storage_limit_mb=sub.storage_limit_mb,
                plugin_used=sub.plugin_used,
                plugin_limit=sub.plugin_limit,
                rollover_credits=sub.rollover_credits,
            )

    async def consume_credits(self, tenant_id: str, amount: int) -> QuotaBalance:
        """扣减租户 credits."""
        async with self._session_factory() as session:
            pk = period_key()
            result = await session.execute(
                select(Subscription).where(
                    Subscription.tenant_id == tenant_id,
                    Subscription.period == pk,
                )
            )
            sub = result.scalar_one_or_none()
            if sub is None:
                raise ValueError(f"No active subscription for tenant {tenant_id}")
            sub.credits_used += amount
            sub.updated_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info("Tenant %s consumed %d credits", tenant_id, amount)
            return await self.get_balance(tenant_id)

    async def rollover_period(self, tenant_id: str) -> None:
        """将上一周期剩余 credits 结转到新周期."""
        async with self._session_factory() as session:
            prev_pk = period_key(offset=-1)
            result = await session.execute(
                select(Subscription).where(
                    Subscription.tenant_id == tenant_id,
                    Subscription.period == prev_pk,
                )
            )
            old_sub = result.scalar_one_or_none()
            if old_sub is None:
                return
            remaining = max(0, old_sub.credits_total - old_sub.credits_used)
            new_pk = period_key()
            result2 = await session.execute(
                select(Subscription).where(
                    Subscription.tenant_id == tenant_id,
                    Subscription.period == new_pk,
                )
            )
            new_sub = result2.scalar_one_or_none()
            if new_sub is None:
                new_sub = Subscription(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    period=new_pk,
                    credits_total=old_sub.credits_total,
                    rollover_credits=remaining,
                )
                session.add(new_sub)
            else:
                new_sub.rollover_credits = remaining
            await session.commit()
            logger.info("Rolled over %d credits for tenant %s", remaining, tenant_id)

    async def rollover_all_active(self) -> int:
        """批量结转所有活跃租户，返回处理数量."""
        count = 0
        async with self._session_factory() as session:
            prev_pk = period_key(offset=-1)
            result = await session.execute(
                select(Subscription.tenant_id).where(
                    Subscription.period == prev_pk
                ).distinct()
            )
            tenant_ids = [row[0] for row in result.fetchall()]
        for tid in tenant_ids:
            await self.rollover_period(tid)
            count += 1
        return count
'''
    text = text[:billing_idx] + new_billing + text[billing_end:]
    print("[OK] billing.py 已统一为 ORM 版")
else:
    print("[INFO] billing.py 无内存版残留，跳过重写")

# ──────────────────────────────────────────────
# STEP 4: 确保 _check_feature_access 签名完整
# ──────────────────────────────────────────────
# 检查是否还有孤立的 "def _check_feature_access(" 后面不跟参数
broken_sig = re.search(
    r"def _check_feature_access\(\s*\n(?!\s+self)", text
)
if broken_sig:
    print("[WARN] 仍存在断裂签名，尝试修复...")
    text = text[:broken_sig.start()] + \
        "def _check_feature_access(\n        self, features: dict[str, Any] | None, plugin_id: str\n    ) -> bool:" + \
        text[broken_sig.end():]
    print("[OK] 签名已修复")
else:
    print("[OK] _check_feature_access 签名完整")

# ──────────────────────────────────────────────
# STEP 5: 写回文件
# ──────────────────────────────────────────────
final_lines = text.split("\n")
print(f"[INFO] 最终行数: {len(final_lines)}")

# 验证：_check_feature_access 应只出现合理次数
cnt = text.count("_check_feature_access")
print(f"[CHECK] _check_feature_access 出现 {cnt} 次（预期 2-3 次：定义+调用）")

# 验证：不应有 self._balances
if "self._balances" in text:
    print("[WARN] 仍存在 self._balances 残留！")
else:
    print("[CHECK] 无内存版残留 ✓")

# 验证：billing.py 文件头只出现一次
billing_count = text.count("#=== File: backend/app/core/billing.py ===")
print(f"[CHECK] billing.py 文件头出现 {billing_count} 次（预期 1）")

SRC.write_text(text, encoding="utf-8")
print(f"\n[DONE] 已写回 {SRC}")
print("       请重新运行: python docs\\soft-copyright\\make_html.py")