# -*- coding: utf-8 -*-
"""fix_source_v3.py - 第三轮修复：清理重复 billing 块 + 补回调用"""
import re, pathlib

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
text = SRC.read_text(encoding="utf-8")
print(f"[INFO] 读入 {len(text.splitlines())} 行")

# ── STEP 1: 删除多余的 billing.py 块（保留最后一个） ──
hdr = "#=== File: backend/app/core/billing.py ==="
positions = [m.start() for m in re.finditer(re.escape(hdr), text)]
print(f"[INFO] billing.py 文件头出现 {len(positions)} 次，位置: {positions}")

if len(positions) >= 2:
    # 找每个 billing 块的结束位置（下一个 #=== File: 或文件末尾）
    next_hdr = re.compile(r"\n#=== File: ")
    # 删除第一个 billing 块（从第一个头到第二个头之前）
    first_start = positions[0]
    # 第一个块的结束 = 第二个块的开始
    second_start = positions[1]
    # 往前回退到第二个块前面的换行
    block_end = second_start
    # 确保不删掉第二个块前面的换行
    if block_end > 0 and text[block_end - 1] == '\n':
        pass  # 保留换行
    removed = text[first_start:block_end]
    print(f"[INFO] 删除第一个 billing 块: {len(removed.splitlines())} 行")
    text = text[:first_start] + text[block_end:]
    print(f"[OK] 删除后 billing 文件头出现 {text.count(hdr)} 次")

# ── STEP 2: 确认无 self._balances 残留 ──
if "self._balances" in text:
    print("[WARN] 仍有 self._balances，定位...")
    for i, ln in enumerate(text.splitlines(), 1):
        if "self._balances" in ln:
            print(f"  行 {i}: {ln.rstrip()}")
else:
    print("[CHECK] 无 self._balances 残留 ✓")

# ── STEP 3: 检查 _check_feature_access ──
cnt = text.count("_check_feature_access")
print(f"[CHECK] _check_feature_access 出现 {cnt} 次")
if cnt < 2:
    # 找到定义处，在其后补一个调用示例（在 register_plugin 方法内）
    # 先找 register_plugin 中是否有调用
    if "self._check_feature_access(" not in text:
        # 在 _check_feature_access 定义结束后找合适位置插入调用
        m = re.search(r"(def _check_feature_access\([^)]*\)[^:]*:.*?\n(?:        .*\n)*)", text)
        if m:
            print("[INFO] 在 register_plugin 中补回 _check_feature_access 调用...")
            # 找 register_plugin 方法
            reg_m = re.search(r"(    async def register_plugin\([^)]*\)[^:]*:\n)", text)
            if reg_m:
                insert_pos = reg_m.end()
                call_code = (
                    '        # 校验插件功能权限\n'
                    '        if not self._check_feature_access(\n'
                    '            plugin_spec.get("features"), plugin_id\n'
                    '        ):\n'
                    '            raise PermissionError(\n'
                    '                f"Plugin {plugin_id} requires features not enabled"\n'
                    '            )\n'
                )
                text = text[:insert_pos] + call_code + text[insert_pos:]
                print("[OK] 调用已补回")
            else:
                print("[WARN] 未找到 register_plugin，跳过")
        else:
            print("[WARN] 未找到 _check_feature_access 定义，跳过")

# ── STEP 4: 最终验证 ──
print(f"\n===== 最终验证 =====")
print(f"  billing.py 文件头: {text.count(hdr)} 次 (预期 1)")
print(f"  self._balances:    {'有残留!' if 'self._balances' in text else '无 ✓'}")
print(f"  _check_feature_access: {text.count('_check_feature_access')} 次 (预期 2-3)")
print(f"  总行数: {len(text.splitlines())}")

SRC.write_text(text, encoding="utf-8")
print(f"\n[DONE] 已写回 {SRC}")