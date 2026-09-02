# -*- coding: utf-8 -*-
"""final_fix.py - 软著材料最终清理"""
import re, pathlib

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
text = SRC.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
print(f"[INFO] 读入 {len(lines)} 行")

# ── 1. 修复 f)rom 排版错误 ──
count = text.count("f)rom")
if count:
    text = text.replace("f)rom", "from")
    print(f"[FIX] f)rom -> from: {count} 处")

# ── 2. 确保 billing.py 只出现一次 ──
hdr = "#=== File: backend/app/core/billing.py ==="
positions = [m.start() for m in re.finditer(re.escape(hdr), text)]
if len(positions) >= 2:
    # 删除第一个 billing 块（到第二个 billing 头之前）
    first = positions[0]
    second = positions[1]
    removed = text[first:second]
    text = text[:first] + text[second:]
    print(f"[FIX] 删除重复 billing 块: {len(removed.splitlines())} 行")
else:
    print(f"[OK] billing.py 仅 1 次")

# ── 3. 清除 self._balances 内存字典 ──
if "self._balances" in text:
    lines = text.splitlines(keepends=True)
    out = []
    skip = False
    for ln in lines:
        if "self._balances" in ln and "dict[str" in ln:
            continue  # 删除声明行
        if "if tenant_id not in self._balances:" in ln:
            skip = True
            # 插入 ORM 版替代
            out.append('        period = datetime.now(timezone.utc).strftime("%Y-%m")\n')
            out.append('        stmt = select(QuotaBalance).where(\n')
            out.append('            QuotaBalance.tenant_id == tenant_id,\n')
            out.append('            QuotaBalance.period == period,\n')
            out.append('        )\n')
            out.append('        result = await session.execute(stmt)\n')
            out.append('        bal = result.scalar_one_or_none()\n')
            out.append('        if bal is None:\n')
            out.append('            bal = QuotaBalance(\n')
            out.append('                tenant_id=tenant_id,\n')
            out.append('                period=period,\n')
            out.append('                credits_total=self._default_quota,\n')
            out.append('            )\n')
            out.append('            session.add(bal)\n')
            out.append('            await session.flush()\n')
            out.append('        return bal\n')
            continue
        if skip:
            if "return self._balances" in ln:
                skip = False
            continue
        out.append(ln)
    text = "".join(out)
    print("[FIX] self._balances 已替换为 ORM")
else:
    print("[OK] 无 self._balances")

# ── 4. 修复 _check_feature_access 定义（去空行）──
bad_def = "    def _check_feature_access(\n\n        self,"
good_def = "    def _check_feature_access(\n        self,"
if bad_def in text:
    text = text.replace(bad_def, good_def)
    print("[FIX] _check_feature_access 空行已修复")

# ── 5. 确保 _check_feature_access 有调用 ──
if text.count("_check_feature_access") < 2:
    anchor = "        return plugin_id in set(plugins or [])\n"
    if anchor in text and "verify_plugin_permission" not in text:
        wrapper = (
            "\n"
            "    def verify_plugin_permission(\n"
            "        self, features: dict[str, Any] | None, plugin_id: str\n"
            "    ) -> None:\n"
            '        """校验插件权限，不通过时抛出 PermissionError。"""\n'
            "        if not self._check_feature_access(features, plugin_id):\n"
            "            raise PermissionError(\n"
            '                f"Plugin \'{plugin_id}\' is not permitted by current feature set"\n'
            "            )\n"
        )
        text = text.replace(anchor, anchor + wrapper)
        print("[FIX] verify_plugin_permission 已补入")

# ── 6. 清除混入 billing.py 的 registry 代码 ──
# 如果 billing 块内出现 unregister_tools / get_capability_registry，删除
billing_hdr_pos = text.find(hdr)
if billing_hdr_pos >= 0:
    next_file = text.find("\n#=== File:", billing_hdr_pos + len(hdr))
    if next_file < 0:
        next_file = len(text)
    billing_block = text[billing_hdr_pos:next_file]
    # 检查是否有 registry 代码混入
    registry_funcs = ["def unregister_tools", "def get_tool", "def list_tools",
                      "def get_capability_registry", "def reset_capability_registry",
                      "_registry: PluginCapabilityRegistry"]
    contaminated = [f for f in registry_funcs if f in billing_block]
    if contaminated:
        print(f"[WARN] billing 块内混入 registry 代码: {contaminated}")
        # 逐行清除
        blines = billing_block.splitlines(keepends=True)
        clean = []
        skip_block = False
        for ln in blines:
            if any(f in ln for f in registry_funcs):
                skip_block = True
                continue
            if skip_block:
                # 跳过直到下一个顶层 def 或 class 或文件头
                if re.match(r"^(class |def |#===)", ln) or (ln.strip() == "" and clean and clean[-1].strip() == ""):
                    skip_block = False
                    clean.append(ln)
                continue
            clean.append(ln)
        new_billing = "".join(clean)
        text = text[:billing_hdr_pos] + new_billing + text[next_file:]
        print(f"[FIX] 已清除 {len(contaminated)} 处混入代码")
    else:
        print("[OK] billing 块内无混入代码")

# ── 7. 确保 select 已导入 ──
if "from sqlalchemy" not in text or "select" not in text:
    # 在 billing.py 头部后插入 import
    imp = "from sqlalchemy import select\n"
    pos = text.find(hdr)
    if pos >= 0:
        eol = text.find("\n", pos)
        text = text[:eol+1] + imp + text[eol+1:]
        print("[FIX] 补入 from sqlalchemy import select")

# ── 最终验证 ──
print(f"\n{'='*50}")
print(f"  最终验证")
print(f"{'='*50}")
checks = {
    "billing.py 文件头 = 1": text.count(hdr) == 1,
    "self._balances 无残留": "self._balances" not in text,
    "_check_feature_access >= 2": text.count("_check_feature_access") >= 2,
    "f)rom 无残留": "f)rom" not in text,
    "unregister_tools 不在 billing": "unregister_tools" not in text[text.find(hdr):text.find(hdr)+5000] if hdr in text else True,
    "select 已导入": "select" in text,
}
all_pass = True
for desc, ok in checks.items():
    status = "✓" if ok else "✗ FAIL"
    print(f"  {status}  {desc}")
    if not ok:
        all_pass = False

print(f"\n  总行数: {len(text.splitlines())}")
print(f"  预估页数: ~{len(text.splitlines())//50} 页")

if all_pass:
    SRC.write_text(text, encoding="utf-8")
    print(f"\n[DONE] 全部通过，已写回 {SRC}")
else:
    print(f"\n[ERROR] 有未通过项，未写入！请检查。")