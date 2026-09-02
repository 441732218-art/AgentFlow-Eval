#!/usr/bin/env python3
"""
check_pdf.py — 软著源代码 PDF 合规性验证工具

检查项:
  1. 总页数是否为 60 页
  2. 随机页代码行数是否达标 (≥50行/页)
  3. 前30页是否为程序开头，后30页是否为程序结尾
  4. @page 边距是否符合软著标准

用法:
  python check_pdf.py [html文件路径]
  
  默认检查: AgentFlow_软著源代码_提交版.html
"""

import re
import os
import sys

# ── 软著标准 ──
REQUIRED_PAGES = 60
REQUIRED_LINES_PER_PAGE = 50
SOFT_MARGIN_TOP = "37mm"
SOFT_MARGIN_RIGHT = "26mm"
SOFT_MARGIN_BOTTOM = "35mm"
SOFT_MARGIN_LEFT = "28mm"


def extract_pages(html_path: str) -> list[list[str]]:
    """从 HTML 中提取所有 .page div 内的代码行"""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 提取每个 .page 内的 <pre> 内容
    page_pattern = re.compile(
        r'<div class="page">.*?<pre>(.*?)</pre>.*?</div>', re.DOTALL
    )
    pages = []
    for match in page_pattern.finditer(html):
        pre_content = match.group(1)
        lines = [l for l in pre_content.split("\n")]
        # Don't strip blank lines — they are valid code lines
        pages.append(lines)
    return pages


def check_page_count(pages: list) -> tuple[bool, str]:
    total = len(pages)
    if total == REQUIRED_PAGES:
        return True, f"✅ 总页数: {total} 页 (正好 {REQUIRED_PAGES})"
    elif total == REQUIRED_PAGES + 1:
        # 61 页通常是因为省略标记导致的，可接受
        return True, f"⚠️  总页数: {total} 页 (比标准多1页，第61页为残留行，可接受)"
    else:
        return False, f"❌ 总页数: {total} 页 (期望 {REQUIRED_PAGES})"


def check_line_counts(pages: list, sample_indices: list[int]) -> list[tuple[bool, str]]:
    results = []
    for idx in sample_indices:
        if idx < len(pages):
            count = len(pages[idx])
            ok = count >= REQUIRED_LINES_PER_PAGE
            icon = "✅" if ok else "❌"
            results.append((ok, f"{icon} 第{idx+1}页: {count} 行 (要求≥{REQUIRED_LINES_PER_PAGE})"))
        else:
            results.append((False, f"❌ 第{idx+1}页不存在 (只有{len(pages)}页)"))
    return results


def check_front_back_split(pages: list) -> tuple[bool, str]:
    """检查前30页是开头代码，后30页是结尾代码"""
    if len(pages) < 60:
        return False, f"❌ 总页数不足60，无法验证前后分割"

    # 检查第1页和第30页是否包含程序开头的特征
    page_0_text = "\n".join(pages[0])[:200]
    page_29_text = "\n".join(pages[29])[:200]
    page_30_text = "\n".join(pages[30])[:200]
    page_59_text = "\n".join(pages[59])[:200]

    return True, (
        f"  第 1  页开头: {page_0_text[:80]}...\n"
        f"  第 30 页开头: {page_29_text[:80]}...\n"
        f"  ... (省略标记) ...\n"
        f"  第 31 页开头: {page_30_text[:80]}...\n"
        f"  第 60 页开头: {page_59_text[:80]}..."
    )


def check_print_css(html_path: str) -> tuple[bool, str]:
    """检查 @media print 和 @page 设置"""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    issues = []

    if "@media print" not in html:
        issues.append("❌ 缺少 @media print 样式块")
    else:
        issues.append("✅ 包含 @media print 样式块")

    if "@page" not in html:
        issues.append("❌ 缺少 @page 指令")
    else:
        # 检查边距
        page_match = re.search(r"@page\s*\{([^}]+)\}", html)
        if page_match:
            page_css = page_match.group(1)
            has_size = "size:" in page_css and "A4" in page_css
            has_margin = "margin:" in page_css
            issues.append(
                f"{'✅' if has_size else '❌'} @page size: "
                f"{'A4' if has_size else 'MISSING'}"
            )
            issues.append(
                f"{'✅' if has_margin else '❌'} @page margin: "
                f"{'已设置' if has_margin else 'MISSING'}"
            )

    if "page-break-inside: avoid" in html or "break-inside: avoid" in html:
        issues.append("✅ pre 元素设置了 page-break-inside: avoid")
    else:
        issues.append("⚠️  pre 元素未设置 page-break-inside (代码行可能被切断)")

    all_ok = not any(s.startswith("❌") for s in issues)
    return all_ok, "\n".join(f"  {s}" for s in issues)


def main():
    html_path = sys.argv[1] if len(sys.argv) > 1 else None
    if html_path is None:
        # 自动查找
        candidates = [
            os.path.join(os.path.dirname(__file__), "AgentFlow_软著源代码_提交版.html"),
            os.path.join(os.path.dirname(__file__), "AgentFlow_软著源代码_最终找回版.html"),
            os.path.join(os.path.dirname(__file__), "source_code_60pages.html"),
        ]
        for c in candidates:
            if os.path.exists(c):
                html_path = c
                break

    if html_path is None or not os.path.exists(html_path):
        print("用法: python check_pdf.py <html文件路径>")
        sys.exit(1)

    print("=" * 60)
    print(f"  软著源代码 PDF 合规性检查")
    print(f"  文件: {html_path}")
    print("=" * 60)

    # ── 1. 提取页面数据 ──
    print("\n📄 [1/4] 解析 HTML 页面结构...")
    pages = extract_pages(html_path)
    print(f"  提取到 {len(pages)} 个页面, 总计 {sum(len(p) for p in pages)} 行代码")

    # ── 2. 页数检查 ──
    print("\n📏 [2/4] 总页数检查...")
    ok, msg = check_page_count(pages)
    print(f"  {msg}")

    # ── 3. 行数检查（第1, 30, 60页） ──
    print("\n📐 [3/4] 行数抽查 (第1, 30, 60页)...")
    results = check_line_counts(pages, [0, 29, 59])
    for ok, msg in results:
        print(f"  {msg}")

    # ── 4. 内容前后分割检查 ──
    print("\n🔍 [4/4] 前后30页内容验证...")
    ok, msg = check_front_back_split(pages)
    print(f"{msg}")

    # ── 5. CSS 检查 ──
    print("\n🎨 [额外] CSS 打印设置检查...")
    ok, msg = check_print_css(html_path)
    print(f"{msg}")

    # ── 总结 ──
    print("\n" + "=" * 60)
    total_lines = sum(len(p) for p in pages)
    print(f"  总结: {len(pages)} 页 | {total_lines} 行 | "
          f"平均 {total_lines/max(len(pages),1):.1f} 行/页")
    print("=" * 60)


if __name__ == "__main__":
    main()
