#!/usr/bin/env python3
"""
clean_html.py – 源程序鉴别材料合规清洗脚本

清洗内容：
1. 移除每行开头的行号（XXXX | 模式）
2. 移除机器生成的 8 行文件头注释块（软件名称、版本号、著作权人、文件路径、功能描述、代码行数统计）
3. 移除孤立的版权声明行（如 "# © 2026 AgentFlow-Eval"）
4. 保持每页 50 行、总计 60 页的软著规范，不足时空行补齐
5. 保留真实代码逻辑注释（如 # parse .env.docker）
6. 不破坏 HTML 分页标签、页眉页脚结构
"""

import re
import sys

INPUT = "docs/soft-copyright/源程序鉴别材料.html"
OUTPUT = "docs/soft-copyright/source_code_clean.html"
LINES_PER_PAGE = 50
TARGET_PAGES = 60


def strip_line_number(line: str) -> str:
    """Remove leading line number pattern like '0001 | ' or '27869 | '."""
    return re.sub(r"^\d{4,5} \| ", "", line)


def is_machine_header_line(line: str) -> bool:
    """Check if a (stripped) line is part of machine-generated file header."""
    stripped = line.strip()
    # 77 '=' delimiters
    if re.match(r"^# ={75,}$", stripped):
        return True
    # Software name, version, author, file path, description, line count
    if stripped.startswith("# 软件名称：AgentFlow-Eval"):
        return True
    if stripped.startswith("# 版本号：V1.0"):
        return True
    if stripped.startswith("# 著作权人：李凯昕"):
        return True
    if stripped.startswith("# 文件路径："):
        return True
    if stripped.startswith("# 功能描述："):
        return True
    if stripped.startswith("# 本文件代码行数："):
        return True
    # Copyright line (both © and (c) notations)
    if re.match(r"^#\s*©\s*\d{4}", stripped):
        return True
    if re.match(r"^#\s*\(c\)\s*\d{4}", stripped, re.IGNORECASE):
        return True
    return False


def clean_and_pad_pre_block(pre_content: str) -> str:
    """
    Clean one <pre class='ca'> block: remove line numbers & machine headers,
    then pad to exactly LINES_PER_PAGE lines.
    Returns the content string (no leading/trailing newlines).
    """
    raw_lines = pre_content.split("\n")
    cleaned = []

    for raw_line in raw_lines:
        stripped_line = strip_line_number(raw_line)
        # Skip machine-generated header lines
        if is_machine_header_line(stripped_line):
            continue
        # Also skip purely empty lines that were just part of header spacing
        if stripped_line == "" and len(cleaned) == 0 and raw_line.strip() == "":
            continue  # skip leading empty from the \n after <pre>
        cleaned.append(stripped_line)

    # Trim trailing empty lines (from trailing \n before </pre>)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    # Pad to exactly LINES_PER_PAGE
    current = len(cleaned)
    if current < LINES_PER_PAGE:
        cleaned.extend([""] * (LINES_PER_PAGE - current))
    elif current > LINES_PER_PAGE:
        # Trim to exact - better to lose some padding lines
        cleaned = cleaned[:LINES_PER_PAGE]

    return "\n".join(cleaned)


def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"[1] 读取 HTML: {INPUT}")
    print(f"    HTML 总长度: {len(html)} 字符")

    # Find all <pre class="ca"> blocks
    pattern = r'(<pre class="ca">)(.*?)(</pre>)'
    pre_blocks = list(re.finditer(pattern, html, re.DOTALL))
    print(f"[2] 发现 {len(pre_blocks)} 个 <pre> 代码块")

    if len(pre_blocks) != TARGET_PAGES:
        print(f"    ⚠ 期望 {TARGET_PAGES} 个代码块, 实际 {len(pre_blocks)} 个")

    # Process each block and build new HTML by position
    total_removed_lines = 0
    total_before_pad = 0
    last_end = 0
    parts = []

    for idx, m in enumerate(pre_blocks):
        pre_open = m.group(1)
        pre_content = m.group(2)
        pre_close = m.group(3)

        # Add HTML before this pre block
        parts.append(html[last_end:m.start()])

        before_lines = len(pre_content.strip().split("\n"))

        # Remove line numbers, machine headers, and pad to 50 lines
        padded = clean_and_pad_pre_block(pre_content)
        after_pad_lines = len(padded.split("\n"))

        removed = before_lines - after_pad_lines
        total_removed_lines += removed
        total_before_pad += after_pad_lines

        # Build new pre block - padded already has exactly 50 lines
        new_block = pre_open + "\n" + padded + pre_close
        parts.append(new_block)

        last_end = m.end()

        if idx < 3 or idx == len(pre_blocks) - 1:
            print(f"    页面 {idx+1}: {before_lines} 行 → 补齐至 {after_pad_lines} 行 (移除 {removed} 行)")

        # Verify padding
        assert after_pad_lines == LINES_PER_PAGE, \
            f"页面 {idx+1} 填充后行数={after_pad_lines}, 期望={LINES_PER_PAGE}"

    # Add remaining HTML after last pre block
    parts.append(html[last_end:])

    # Rebuild HTML
    print(f"\n[3] 重建 HTML ...")
    result = "".join(parts)

    # Write output
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"[4] 输出文件: {OUTPUT}")
    print(f"    文件大小: {len(result)} 字符")
    print(f"    共移除机器生成行: {total_removed_lines} 行")
    print(f"    补齐前总行数: {total_before_pad} → 补齐后总行数: {TARGET_PAGES * LINES_PER_PAGE}")

    # Verify the output
    verify_blocks = list(re.finditer(pattern, result, re.DOTALL))
    all_50 = True
    for idx, m in enumerate(verify_blocks):
        content = m.group(2).strip("\n")
        lines = content.split("\n")
        non_empty = [l for l in lines if l.strip()]
        if len(lines) != LINES_PER_PAGE:
            print(f"    ⚠ 页面 {idx+1}: {len(lines)} 行 (期望 {LINES_PER_PAGE})")
            all_50 = False

    if all_50:
        print(f"[5] 验证: 全部 {TARGET_PAGES} 页每页 {LINES_PER_PAGE} 行 ✅")
    else:
        print(f"[5] 验证: 存在行数异常 ❌")

    # Verify no line numbers remain
    line_number_count = len(re.findall(r"^\d{4,5} \| ", result, re.MULTILINE))
    print(f"    残留行号: {line_number_count} 处 (期望 0)")
    if line_number_count > 0:
        # Show where they are
        for m in re.finditer(r"^\d{4,5} \| ", result, re.MULTILINE):
            ctx = result[max(0, m.start()-20):m.end()+60]
            print(f"      残留: ...{repr(ctx[:100])}...")

    # Verify no machine header lines remain
    header_count = len(re.findall(r"# 文件路径：backend/", result))
    print(f"    残留机器注释 '文件路径': {header_count} 处 (期望 0)")

    print(f"\n[6] ✅ 清洗完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
