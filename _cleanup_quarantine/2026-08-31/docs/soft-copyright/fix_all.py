# -*- coding: utf-8 -*-
"""fix_all.py - 软著源程序鉴别材料全量修复"""
import re, pathlib, sys

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
BAK = SRC.with_suffix(".txt.bak")

if not SRC.exists():
    print(f"[ERROR] 文件不存在: {SRC}")
    sys.exit(1)

# 备份
BAK.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
print(f"[BAK] 已备份 -> {BAK}")

text = SRC.read_text(encoding="utf-8")
orig_lines = len(text.splitlines())
print(f"[INFO] 读入 {orig_lines} 行")
fixes_applied = []

# ═══════════════════════════════════════════════════════════
# FIX-1: 修复 f)rom 排版错误（中等）
# ═══════════════════════════════════════════════════════════
cnt = text.count("f)rom ")
if cnt:
    text = text.replace("f)rom ", "from ")
    fixes_applied.append(f"FIX-1: f)rom -> from ({cnt} 处)")
    print(f"[FIX-1] f)rom -> from: {cnt} 处")
else:
    print("[OK-1] 无 f)rom 错误")

# ═══════════════════════════════════════════════════════════
# FIX-2: 删除重复的 billing.py 块（严重）
# ═══════════════════════════════════════════════════════════
HDR = "#=== File: backend/app/core/billing.py ==="
positions = [m.start() for m in re.finditer(re.escape(HDR), text)]
if len(positions) >= 2:
    # 保留最后一个完整块，删除前面所有重复块
    for i in range(len(positions) - 1):
        start = positions[i]
        end = positions[i + 1]
        removed = text[start:end]
        text = text[:start] + text[end:]
        # 重新计算位置
        positions = [m.start() for m in re.finditer(re.escape(HDR), text)]
    fixes_applied.append(f"FIX-2: 删除重复 billing.py 块 ({len(positions)} -> 1)")
    print(f"[FIX-2] 删除重复 billing 块，保留 1 个")
else:
    print(f"[OK-2] billing.py 仅 {len(positions)} 次")

# ═══════════════════════════════════════════════════════════
# FIX-3: 清除 billing.py 块内混入的 registry.py 代码（严重）
# ═══════════════════════════════════════════════════════════
billing_start = text.find(HDR)
if billing_start >= 0:
    next_file = text.find("\n#=== File:", billing_start + len(HDR))
    if next_file < 0:
        next_file = len(text)
    billing_block = text[billing_start:next_file]

    # registry.py 特征代码
    registry_patterns = [
        r"def unregister_tools\(self.*?\n(?:(?:        .*\n)*)",
        r"def get_tool\(self.*?\n(?:(?:        .*\n)*)",
        r"def list_tools\(self.*?\n(?:(?:        .*\n)*)",
        r"def get_capability_registry\(\).*?\n(?:(?:    .*\n)*)",
        r"def reset_capability_registry\(\).*?\n(?:(?:    .*\n)*)",
        r"_registry:\s*PluginCapabilityRegistry.*?\n",
        r"_registry\s*=\s*None.*?\n",
    ]
    removed_count = 0
    for pat in registry_patterns:
        matches = list(re.finditer(pat, billing_block))
        for m in reversed(matches):
            billing_block = billing_block[:m.start()] + billing_block[m.end():]
            removed_count += 1

    if removed_count:
        text = text[:billing_start] + billing_block + text[next_file:]
        fixes_applied.append(f"FIX-3: 清除 billing 内 registry 混入代码 ({removed_count} 处)")
        print(f"[FIX-3] 清除混入代码: {removed_count} 处")
    else:
        print("[OK-3] billing 块内无混入代码")
else:
    print("[WARN-3] 未找到 billing.py 文件头")

# ═══════════════════════════════════════════════════════════
# FIX-4: 修复截断的 _check_feature_access（严重）
# ═══════════════════════════════════════════════════════════
# 模式A: 定义后紧跟另一个 def（无函数体）
truncated_pattern = re.compile(
    r"(    def _check_feature_access\(\s*\n)"   # 签名行
    r"(?:\s*\n)*"                                # 可能的空行
    r"(    def \w+)"                             # 紧跟另一个 def
)
m = truncated_pattern.search(text)
if m:
    # 替换为完整定义
    complete_def = (
        "    def _check_feature_access(\n"
        "        self,\n"
        "        features: dict[str, Any] | None,\n"
        "        plugin_id: str,\n"
        "    ) -> bool:\n"
        '        """检查当前特性集是否允许访问指定插件。"""\n'
        "        if features is None:\n"
        "            return True\n"
        "        plugins = features.get('enabled_plugins')\n"
        "        if plugins is None:\n"
        "            return True\n"
        "        return plugin_id in set(plugins or [])\n"
        "\n"
    )
    text = text[:m.start()] + complete_def + text[m.start(2):]
    fixes_applied.append("FIX-4: 补全 _check_feature_access 完整定义")
    print("[FIX-4] _check_feature_access 已补全")
else:
    # 检查是否已有完整定义
    if "def _check_feature_access(" in text:
        # 检查是否有函数体
        idx = text.find("def _check_feature_access(")
        snippet = text[idx:idx+500]
        if "return" in snippet:
            print("[OK-4] _check_feature_access 已完整")
        else:
            print("[WARN-4] _check_feature_access 可能不完整，请人工检查")
    else:
        print("[WARN-4] 未找到 _check_feature_access")

# ═══════════════════════════════════════════════════════════
# FIX-5: 统一 BillingService 为 ORM 版（严重）
# ═══════════════════════════════════════════════════════════
if "self._balances" in text:
    lines = text.splitlines(keepends=True)
    out = []
    skip_until_return = False
    replaced = False

    for i, ln in enumerate(lines):
        # 删除内存字典声明
        if "self._balances" in ln and ("dict[" in ln or "{}" in ln):
            continue

        # 替换内存版 get_balance 逻辑
        if "if tenant_id not in self._balances:" in ln:
            skip_until_return = True
            replaced = True
            # 插入 ORM 版
            out.append('        period = datetime.now(timezone.utc).strftime("%Y-%m")\n')
            out.append("        stmt = select(QuotaBalance).where(\n")
            out.append("            QuotaBalance.tenant_id == tenant_id,\n")
            out.append("            QuotaBalance.period == period,\n")
            out.append("        )\n")
            out.append("        result = await session.execute(stmt)\n")
            out.append("        bal = result.scalar_one_or_none()\n")
            out.append("        if bal is None:\n")
            out.append("            bal = QuotaBalance(\n")
            out.append("                tenant_id=tenant_id,\n")
            out.append("                period=period,\n")
            out.append("                credits_total=self._default_quota,\n")
            out.append("                credits_used=0,\n")
            out.append("            )\n")
            out.append("            session.add(bal)\n")
            out.append("            await session.flush()\n")
            out.append("        return bal\n")
            continue

        if skip_until_return:
            if "return self._balances" in ln:
                skip_until_return = False
            continue

        # 删除其他 self._balances 引用
        if "self._balances" in ln:
            continue

        out.append(ln)

    text = "".join(out)
    if replaced:
        fixes_applied.append("FIX-5: self._balances 内存字典 -> ORM")
        print("[FIX-5] 已替换为 ORM 版")
    else:
        print("[WARN-5] 未找到内存版 get_balance 模式")

    # 确保 select 已导入
    if "from sqlalchemy import select" not in text and "from sqlalchemy" in text:
        text = text.replace(
            "from sqlalchemy",
            "from sqlalchemy import select\nfrom sqlalchemy",
            1
        )
        print("[FIX-5b] 补入 select 导入")
    elif "select" not in text:
        # 在 billing 文件头后插入
        pos = text.find(HDR)
        if pos >= 0:
            eol = text.find("\n", pos)
            text = text[:eol+1] + "from sqlalchemy import select\n" + text[eol+1:]
            print("[FIX-5c] 补入 select 导入")
else:
    print("[OK-5] 无 self._balances")

# ═══════════════════════════════════════════════════════════
# FIX-6: 精简 rbac.py 模块级 docstring（中等）
# ═══════════════════════════════════════════════════════════
rbac_hdr = "#=== File: backend/app/core/rbac.py ==="
rbac_pos = text.find(rbac_hdr)
if rbac_pos >= 0:
    # 找到 docstring（三引号块）
    doc_start = text.find('"""', rbac_pos)
    if doc_start >= 0 and doc_start - rbac_pos < 200:
        doc_end = text.find('"""', doc_start + 3)
        if doc_end >= 0:
            docstring = text[doc_start:doc_end + 3]
            doc_lines = docstring.splitlines()
            if len(doc_lines) > 8:
                # 精简为 5 行
                short_doc = (
                    '"""RBAC - 基于角色的访问控制模块。\n'
                    "\n"
                    "定义企业角色层级、权限矩阵及鉴权装饰器，\n"
                    "支持 FastAPI Depends 和函数装饰器两种使用方式。\n"
                    '"""'
                )
                text = text[:doc_start] + short_doc + text[doc_end + 3:]
                fixes_applied.append(f"FIX-6: rbac.py docstring {len(doc_lines)}行 -> 5行")
                print(f"[FIX-6] rbac docstring: {len(doc_lines)} -> 5 行")
            else:
                print(f"[OK-6] rbac docstring 仅 {len(doc_lines)} 行")
    else:
        print("[OK-6] 未找到 rbac docstring")
else:
    print("[WARN-6] 未找到 rbac.py")

# ═══════════════════════════════════════════════════════════
# 清理：删除连续空行 > 2 的
# ═══════════════════════════════════════════════════════════
text = re.sub(r"\n{4,}", "\n\n\n", text)

# ═══════════════════════════════════════════════════════════
# 最终验证
# ═══════════════════════════════════════════════════════════
print(f"\n{'='*55}")
print(f"  最终验证报告")
print(f"{'='*55}")

checks = [
    ("billing.py 文件头 = 1",     text.count(HDR) == 1),
    ("self._balances 无残留",     "self._balances" not in text),
    ("f)rom 无残留",              "f)rom" not in text),
    ("_check_feature_access 完整", "return plugin_id in set" in text),
    ("registry 未混入 billing",   "unregister_tools" not in text[text.find(HDR):text.find(HDR)+6000] if HDR in text else True),
    ("select 已导入",             "select" in text),
]

all_pass = True
for desc, ok in checks:
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}]  {desc}")
    if not ok:
        all_pass = False

final_lines = len(text.splitlines())
print(f"\n  原始行数: {orig_lines}")
print(f"  修复行数: {final_lines}")
print(f"  预估页数: ~{final_lines // 50} 页")
print(f"  修复项数: {len(fixes_applied)}")
for f in fixes_applied:
    print(f"    - {f}")

if all_pass:
    SRC.write_text(text, encoding="utf-8")
    print(f"\n[DONE] 全部通过 -> 已写回 {SRC}")
else:
    print(f"\n[ABORT] 有未通过项，未写入！请人工检查。")
    sys.exit(1)