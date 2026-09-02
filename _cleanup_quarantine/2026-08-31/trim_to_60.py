#!/usr/bin/env python3
"""trim_to_60.py — 将 raw_source.txt 裁剪为 60 页软著提交版 HTML"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(ROOT, "raw_source.txt")
OUTPUT_FILE = os.path.join(ROOT, "AgentFlow-Eval_源代码_软著提交版.html")
LINES_PER_PAGE = 50
TOTAL_PAGES = 60
FRONT_PAGES = TOTAL_PAGES // 2       # 30
BACK_PAGES = TOTAL_PAGES // 2        # 30
TOTAL_LINES = LINES_PER_PAGE * TOTAL_PAGES  # 3000
HALF_LINES = LINES_PER_PAGE * FRONT_PAGES   # 1500

SOFTWARE_NAME = "AgentFlow 智能体评测管理平台软件"
VERSION = "V1.0"

print("正在读取原始代码...")
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    all_lines = [line.rstrip("\n") for line in f]

total_lines = len(all_lines)
print(f"总行数: {total_lines}")

if total_lines <= TOTAL_LINES:
    print("代码总量未超过60页，将提交全部代码。")
    final_lines = all_lines
else:
    front_lines = all_lines[:HALF_LINES]
    back_lines = all_lines[-HALF_LINES:]
    separator = [
        "",
        "/* ========== 中间部分省略（共省略 {} 行） ========== */".format(
            total_lines - HALF_LINES * 2
        ),
        "",
    ]
    final_lines = front_lines + separator + back_lines
    print(f"已裁剪：保留前 {HALF_LINES} 行 + 省略标记 + 后 {HALF_LINES} 行")

# 重新计算总页数（包含省略标记行）
display_pages = (len(final_lines) + LINES_PER_PAGE - 1) // LINES_PER_PAGE

# 按页切分
pages = []
for i in range(0, len(final_lines), LINES_PER_PAGE):
    pages.append(final_lines[i : i + LINES_PER_PAGE])

# 生成 HTML
html_parts = []
html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{SOFTWARE_NAME} {VERSION} 源程序鉴别材料</title>
<style>
@page{{size:A4 portrait;margin:18mm 12mm 18mm 12mm}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Courier New",Consolas,monospace;font-size:10pt;line-height:1.2;color:#000}}
.page{{page-break-after:always;min-height:255mm;padding:6mm 4mm;position:relative}}
.page:last-child{{page-break-after:auto}}
.header{{border-bottom:1px solid #000;padding-bottom:2px;margin-bottom:6px;
    display:flex;justify-content:space-between;font-weight:bold;font-size:10pt}}
.footer{{position:absolute;bottom:5mm;left:4mm;right:4mm;text-align:center;
    border-top:1px solid #ccc;padding-top:2px;font-size:8pt;color:#555}}
pre{{margin:0;white-space:pre-wrap;word-wrap:break-word;font-family:inherit;
    font-size:10pt;line-height:1.2}}
</style>
</head>
<body>
""")

for idx, chunk in enumerate(pages):
    pn = idx + 1
    code = "\n".join(chunk)
    html_parts.append(f"""
<div class="page">
<div class="header">
<span>{SOFTWARE_NAME} {VERSION}</span>
<span>第{pn}页 / 共{display_pages}页</span>
</div>
<pre>{code}</pre>
<div class="footer">- {pn} -</div>
</div>
""")

html_parts.append("\n</body>\n</html>")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("".join(html_parts))

size_kb = os.path.getsize(OUTPUT_FILE) / 1024
print(f"\n[DONE] 已生成: {OUTPUT_FILE}")
print(f"  总页数: {display_pages}  总行数: {len(final_lines)}  大小: {size_kb:.1f} KB")
print("请使用浏览器打开该文件，按 Ctrl+P 另存为 PDF。")
