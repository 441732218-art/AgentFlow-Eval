#!/usr/bin/env python3
"""
clean_final.py – 终极深度清洗：移除行号、竖线、机器元数据注释块。

清洗目标（针对 <pre class="ca"> 内的每一行）：
1. 行首行号 + 竖线 → 移除，例如 "0115 | from ..." → "from ..."
2. 机器元数据注释行 → 整行移除，包含：
   - 分隔线：   "# =====..." (至少 10 个 =)
   - 软件名称：  "# 软件名称：AgentFlow-Eval"
   - 版本号：    "# 版本号：V1.0"
   - 著作权人：  "# 著作权人：李凯昕"
   - 文件路径：  "# 文件路径：backend/..."
   - 功能描述：  "# 功能描述：..."
   - 代码行数：  "# 本文件代码行数：... 行"
   - 版权声明：  "# (c) 2026 ..."  /  "# © 2026 ..."
3. 保留真实代码注释如 "# parse .env.docker" 不变。
4. 保留所有缩进（空格/制表符）。

用法：
    python clean_final.py
"""

import re
import sys
from pathlib import Path

# ── 路径 ─────────────────────────────────────────────────────────────
ORIG_HTML  = Path(__file__).parent / "源程序鉴别材料.html"
OUTPUT     = Path(__file__).parent / "source_code_FINAL_V2.html"


# ── 编译正则 ──────────────────────────────────────────────────────────

# 行首行号 + 竖线： 1~5 位数字 + 可选空格 + | + 可选空格
RE_LINENO = re.compile(r"^\d{1,5}\s*\|\s*")

# 机器元数据注释行（整行匹配，忽略前导空格）
META_PATTERNS = [
    re.compile(r"^#\s*={10,}\s*$"),                   # 分隔线
    re.compile(r"^#\s*软件名称\s*[：:]"),              # 软件名称
    re.compile(r"^#\s*版本号\s*[：:]"),                # 版本号
    re.compile(r"^#\s*著作权人\s*[：:]"),              # 著作权人
    re.compile(r"^#\s*文件路径\s*[：:]"),              # 文件路径
    re.compile(r"^#\s*功能描述\s*[：:]"),              # 功能描述
    re.compile(r"^#\s*本文件代码行数\s*[：:]"),        # 代码行数
    re.compile(r"^#\s*[©(c)]\s*\d{4}\s+AgentFlow"),   # 版权 ©
    re.compile(r"^#\s*\(c\)\s*\d{4}\s+AgentFlow"),     # 版权 (c)
    re.compile(r"^#\s*\?\s*\d{4}\s+AgentFlow"),        # 版权 ? (编码异常的 ©)
]


def is_metadata_line(line: str) -> bool:
    """判断某行是否为机器元数据注释。"""
    stripped = line.lstrip()
    for pat in META_PATTERNS:
        if pat.match(stripped):
            return True
    return False


def strip_line_number(line: str) -> str:
    """移除行首的行号前缀。"""
    return RE_LINENO.sub("", line, count=1)


def clean_pre_block(pre_content: str) -> str:
    """
    彻底清洗一个 <pre> 块的内容：
    - 步骤一：移除每行行号
    - 步骤二：移除机器元数据注释行
    - 保留：真实代码、真实注释、空行、缩进
    """
    raw_lines = pre_content.split("\n")
    cleaned = []

    for raw_line in raw_lines:
        # 先去除行号
        line = strip_line_number(raw_line)

        # 跳过元数据行（整行删除）
        if is_metadata_line(line):
            continue

        cleaned.append(line)

    # 去除头部连续空行
    while cleaned and cleaned[0].strip() == "":
        cleaned.pop(0)

    # 去除尾部连续空行（保留一个排版空行）
    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()

    return "\n".join(cleaned)


def main() -> int:
    print("=" * 60)
    print("  clean_final.py - 终极深度清洗")
    print("=" * 60)

    # 1. 读取原始 HTML
    if not ORIG_HTML.exists():
        print(f"[ERROR] 找不到输入文件: {ORIG_HTML}")
        return 1

    html = ORIG_HTML.read_text(encoding="utf-8")
    print(f"\n[1] 读取 HTML: {ORIG_HTML.name}")
    print(f"    文件大小: {len(html):,} 字符")

    # 2. 定位所有 <pre class="ca"> ... </pre> 块
    pre_pattern = r'(<pre\s+class="ca">)(.*?)(</pre>)'
    pre_blocks = list(re.finditer(pre_pattern, html, re.DOTALL))
    print(f"[2] 发现 {len(pre_blocks)} 个 <pre class=\"ca\"> 代码块")

    if not pre_blocks:
        pre_pattern = r'(<pre[^>]*>)(.*?)(</pre>)'
        pre_blocks = list(re.finditer(pre_pattern, html, re.DOTALL))
        print(f"    宽松匹配后找到 {len(pre_blocks)} 个 <pre> 块")

    if not pre_blocks:
        print("[ERROR] 未找到任何 <pre> 代码块，终止。")
        return 1

    # 3. 逐块清洗并重组 HTML
    last_end = 0
    parts = []
    stats = []

    for idx, m in enumerate(pre_blocks):
        pre_open = m.group(1)
        pre_content = m.group(2)
        pre_close = m.group(3)

        # 添加本块之前的 HTML
        parts.append(html[last_end : m.start()])

        # 统计清洗前
        raw_lines_count = len([l for l in pre_content.split("\n") if l.strip()])

        # 清洗
        cleaned_content = clean_pre_block(pre_content)
        clean_lines_count = len([l for l in cleaned_content.split("\n") if l.strip()])
        removed = raw_lines_count - clean_lines_count

        # 重建 <pre>
        new_block = pre_open + "\n" + cleaned_content + "\n" + pre_close
        parts.append(new_block)

        last_end = m.end()
        stats.append((raw_lines_count, clean_lines_count, removed))

    # 添加尾部 HTML
    parts.append(html[last_end:])

    # 4. 输出
    result = "".join(parts)
    OUTPUT.write_text(result, encoding="utf-8")

    total_raw = sum(s[0] for s in stats)
    total_clean = sum(s[1] for s in stats)
    total_removed = sum(s[2] for s in stats)

    print(f"\n[3] 输出文件: {OUTPUT.name}")
    print(f"    文件大小: {len(result):,} 字符 ({len(result) - len(html):+d})")
    print(f"    有效行数: {total_raw:,} -> {total_clean:,} (移除 {total_removed} 行)")

    # 5. 验证
    print(f"\n[4] 验证：")

    # 5a. 提取所有 <pre> 内的行
    pre_only = []
    in_pre = False
    for line in result.split("\n"):
        if '<pre class="ca">' in line or re.search(r'<pre\s+class="ca">', line):
            in_pre = True
            continue
        if "</pre>" in line:
            in_pre = False
            continue
        if in_pre:
            pre_only.append(line)

    # 行号残留
    line_no_issues = 0
    for line in pre_only:
        if RE_LINENO.match(line):
            line_no_issues += 1

    if line_no_issues == 0:
        print("    [行号] 残留: 0 处 - OK")
    else:
        print(f"    [行号] 残留: {line_no_issues} 处 - FAIL")
        for line in pre_only:
            if RE_LINENO.match(line):
                print(f"      示例: {repr(line[:80])}")
                break

    # 元数据残留
    meta_issues = 0
    meta_examples = []
    for line in pre_only:
        if is_metadata_line(line):
            meta_issues += 1
            if len(meta_examples) < 3:
                meta_examples.append(line.strip()[:60])

    if meta_issues == 0:
        print("    [元数据] 残留: 0 处 - OK")
    else:
        print(f"    [元数据] 残留: {meta_issues} 处 - FAIL")
        for ex in meta_examples:
            print(f"      示例: {ex!r}")

    # 5b. 抽样检查第 3、30、60 页
    verify_pattern = r'(<pre\s+class="ca">)(.*?)(</pre>)'
    verify_blocks = list(re.finditer(verify_pattern, result, re.DOTALL))
    print(f"\n[5] 抽样检查：")
    for pg in [3, 30, 60]:
        if pg > len(verify_blocks):
            print(f"    第 {pg} 页: 不存在 (共 {len(verify_blocks)} 页)")
            continue

        content = verify_blocks[pg - 1].group(2)
        lines = [l for l in content.split("\n") if l.strip()]

        print(f"\n    第 {pg} 页 ({len(lines)} 有效行):")
        ok = True
        for i, l in enumerate(lines[:10]):
            marker = ""
            if RE_LINENO.match(l):
                marker = " <<< 行号残留!"
                ok = False
            elif is_metadata_line(l):
                marker = " <<< 元数据残留!"
                ok = False
            print(f"      [{i+1}] {l[:80]}{marker}")
        if ok:
            print(f"      -> 检查通过!")
        else:
            print(f"      -> 存在残留!")

    # 5c. HTML 结构完整性
    pre_open_count = len(re.findall(r'<pre\s+class="ca">', result))
    pre_close_count = len(re.findall(r'</pre>', result))
    print(f"\n[6] 结构完整性：")
    print(f"    <pre class=\"ca\">: {pre_open_count}, </pre>: {pre_close_count}")
    if pre_open_count == pre_close_count:
        print("    标签配对: OK")
    else:
        print(f"    标签数量不匹配!")

    print(f"\n{'=' * 60}")
    print(f"  OK! 深度清洗完成!")
    print(f"  输出: {OUTPUT}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

