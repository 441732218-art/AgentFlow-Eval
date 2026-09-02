# -*- coding: utf-8 -*-
"""trim_60pages.py - 裁剪为前30页+后30页"""
import pathlib

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
LINES_PER_PAGE = 50
TOTAL_PAGES = 60
HALF = 30

text = SRC.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
total = len(lines)
print(f"[INFO] 当前 {total} 行, ~{total // LINES_PER_PAGE} 页")

if total <= TOTAL_PAGES * LINES_PER_PAGE:
    print(f"[OK] 已 <= {TOTAL_PAGES} 页, 无需裁剪")
else:
    front = lines[:HALF * LINES_PER_PAGE]          # 前 1500 行
    back  = lines[-(HALF * LINES_PER_PAGE):]       # 后 1500 行

    # 确保 back 从完整文件头开始（避免截断在函数中间）
    # 向后找最近的 #=== File: 头
    start_idx = 0
    for i, ln in enumerate(back):
        if ln.startswith("#=== File:"):
            start_idx = i
            break
    if start_idx > 0:
        print(f"[TRIM] 后30页起始调整: 跳过 {start_idx} 行到文件头")
        back = back[start_idx:]

    # 分隔标记
    sep = [
        "\n",
        "# " + "=" * 60 + "\n",
        "# （此处省略中间部分源代码）\n",
        "# " + "=" * 60 + "\n",
        "\n",
    ]

    result = front + sep + back
    new_total = len(result)
    print(f"[DONE] 裁剪完成: {total} -> {new_total} 行, ~{new_total // LINES_PER_PAGE} 页")

    # 验证
    import re
    headers = re.findall(r"#=== File: (.+?) ===", "".join(result))
    print(f"\n  包含源文件 ({len(headers)} 个):")
    for h in headers:
        print(f"    - {h}")

    # 检查每页有效行数
    print(f"\n  前30页: {len(front)} 行")
    print(f"  后30页: {len(back)} 行")

    SRC.write_text("".join(result), encoding="utf-8")
    print(f"\n[SAVED] -> {SRC}")