# -*- coding: utf-8 -*-
"""fix_source_v5.py - 最终修复"""
import pathlib

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
print(f"[INFO] 读入 {len(lines)} 行")

# ── FIX 1: 删除 self._balances 行 ──
new_lines = []
for ln in lines:
    if "self._balances" in ln and "dict[str, QuotaBalance]" in ln:
        print(f"[FIX1] 删除: {ln.rstrip()}")
        continue
    new_lines.append(ln)
lines = new_lines

# ── FIX 2: 替换 get_balance 方法体（内存版 → ORM 版）──
text = "".join(lines)

old_body = (
    '        if tenant_id not in self._balances:\n'
    '            self._balances[tenant_id] = QuotaBalance(\n'
    '                tenant_id=tenant_id,\n'
    '                period=datetime.now(timezone.utc).strftime("%Y-%m"),\n'
    '                credits_total=self._default_quota,\n'
    '            )\n'
    '        return self._balances[tenant_id]\n'
)

new_body = (
    '        period = datetime.now(timezone.utc).strftime("%Y-%m")\n'
    '        stmt = select(QuotaBalance).where(\n'
    '            QuotaBalance.tenant_id == tenant_id,\n'
    '            QuotaBalance.period == period,\n'
    '        )\n'
    '        result = await session.execute(stmt)\n'
    '        bal = result.scalar_one_or_none()\n'
    '        if bal is None:\n'
    '            bal = QuotaBalance(\n'
    '                tenant_id=tenant_id,\n'
    '                period=period,\n'
    '                credits_total=self._default_quota,\n'
    '            )\n'
    '            session.add(bal)\n'
    '            await session.flush()\n'
    '        return bal\n'
)

if old_body in text:
    text = text.replace(old_body, new_body)
    print("[FIX2] get_balance 已替换为 ORM 版")
else:
    print("[WARN] 未找到 get_balance 旧方法体，尝试逐行匹配...")
    # fallback: 逐行替换
    lines2 = text.splitlines(keepends=True)
    out = []
    skip_until_return = False
    for ln in lines2:
        if "if tenant_id not in self._balances:" in ln:
            skip_until_return = True
            out.append(new_body)
            continue
        if skip_until_return:
            if "return self._balances[tenant_id]" in ln:
                skip_until_return = False
            continue
        out.append(ln)
    text = "".join(out)
    print("[FIX2] get_balance 已替换（fallback 模式）")

# ── FIX 3: 修复 _check_feature_access 定义中的空行 ──
old_def = (
    '    def _check_feature_access(\n'
    '\n'
    '        self, features: dict[str, Any] | None, plugin_id: str\n'
    '    ) -> bool:\n'
)
new_def = (
    '    def _check_feature_access(\n'
    '        self, features: dict[str, Any] | None, plugin_id: str\n'
    '    ) -> bool:\n'
)
if old_def in text:
    text = text.replace(old_def, new_def)
    print("[FIX3] _check_feature_access 定义空行已修复")
else:
    print("[INFO] _check_feature_access 定义格式正常，无需修复")

# ── FIX 4: 在 _check_feature_access 后补公开调用方法 ──
anchor = '        return plugin_id in set(plugins or [])\n'
wrapper = (
    '\n'
    '    def verify_plugin_permission(\n'
    '        self, features: dict[str, Any] | None, plugin_id: str\n'
    '    ) -> None:\n'
    '        """校验插件权限，不通过时抛出 PermissionError。"""\n'
    '        if not self._check_feature_access(features, plugin_id):\n'
    '            raise PermissionError(\n'
    '                f"Plugin \'{plugin_id}\' is not permitted by current feature set"\n'
    '            )\n'
)
if anchor in text and "verify_plugin_permission" not in text:
    text = text.replace(anchor, anchor + wrapper)
    print("[FIX4] verify_plugin_permission 已插入（调用 _check_feature_access）")
else:
    print("[INFO] 跳过 FIX4")

# ── 最终验证 ──
print(f"\n===== 最终验证 =====")
print(f"  self._balances:         {'有残留!' if 'self._balances' in text else '无 ✓'}")
print(f"  _check_feature_access:  {text.count('_check_feature_access')} 次 (预期 3)")
print(f"  billing.py 文件头:      {text.count('#=== File: backend/app/core/billing.py ===')} 次 (预期 1)")
print(f"  总行数:                 {len(text.splitlines())}")

# 确认 select 已导入
if "from sqlalchemy" in text and "select" in text:
    print(f"  sqlalchemy select:      已导入 ✓")
else:
    print(f"  [WARN] 请确认 select 已导入")

SRC.write_text(text, encoding="utf-8")
print(f"\n[DONE] 已写回 {SRC}")
print("       请运行: python docs\\soft-copyright\\make_html.py")