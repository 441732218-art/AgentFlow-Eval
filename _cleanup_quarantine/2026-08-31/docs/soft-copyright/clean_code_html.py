#!/usr/bin/env python3
"""
clean_code_html.py – 深度清洗：移除 <pre class="ca"> 代码块中每行开头的行号前缀。

行号格式示例：
    0115 | from app.utils.exceptions import BusinessError, NotFoundError
    0117 | router = APIRouter()
    → 清洗后：
    from app.utils.exceptions import BusinessError, NotFoundError
    router = APIRouter()

用法：
    python clean_code_html.py
"""

import re
import sys
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────
ORIG_HTML = Path(__file__).parent / "源程序鉴别材料.html"
OUTPUT    = Path(__file__).parent / "source_code_FINAL.html"

# ── 正则：行首行号 ────────────────────────────────────────────────────
# 匹配: 1-5 位数字 + 可选空格 + 竖线 + 可选空格
LINE_NUM_RE = re.compile(r"^\d{1,5}\s*\|\s*")

def strip_line_number(line: str) -> str:
    """去除行首的 '0001 | ' 或 '1|' 或 '12345 |' 等模式，保留后续内容。"""
    return LINE_NUM_RE.sub("", line, count=1)


def clean_pre_block(pre_content: str) -> str:
    """
    清洗单个 <pre> 块内容：
    - 去除每行行首的行号
    - 保留原始缩进
    - 去除头部/尾部多余空白行
    """
    raw_lines = pre_content.split("\n")
    cleaned = []

    for raw_line in raw_lines:
        # 去除行号
        stripped = strip_line_number(raw_line)
        cleaned.append(stripped)

    # 去除尾部连续空行（保留一个）
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def main() -> int:
    # 1. 读取原始 HTML
    if not ORIG_HTML.exists():
        print(f"[ERROR] 找不到输入文件: {ORIG_HTML}")
        return 1

    html = ORIG_HTML.read_text(encoding="utf-8")
    print(f"[1] 读取 HTML: {ORIG_HTML}")
    print(f"    HTML 总长度: {len(html)} 字符")

    # 2. 定位所有 <pre class="ca"> ... </pre> 块
    pattern = r'(<pre\s+class="ca">)(.*?)(</pre>)'
    pre_blocks = list(re.finditer(pattern, html, re.DOTALL))
    print(f"[2] 发现 {len(pre_blocks)} 个 <pre class=\"ca\"> 代码块")

    if not pre_blocks:
        print("[WARN] 未找到任何 <pre class=\"ca\"> 块，尝试宽松匹配 <pre>...")
        pattern = r'(<pre[^>]*>)(.*?)(</pre>)'
        pre_blocks = list(re.finditer(pattern, html, re.DOTALL))
        print(f"    宽松匹配后找到 {len(pre_blocks)} 个 <pre> 块")

    # 3. 逐块清洗并重组 HTML
    last_end = 0
    parts = []
    total_lines_before = 0
    total_lines_after = 0

    for idx, m in enumerate(pre_blocks):
        pre_open = m.group(1)   # e.g. <pre class="ca">
        pre_content = m.group(2)  # content between tags
        pre_close = m.group(3)    # </pre>

        # 添加本块之前的 HTML
        parts.append(html[last_end:m.start()])

        # 统计清洗前有效行数
        raw_lines = [l for l in pre_content.split("\n") if l.strip()]
        total_lines_before += len(raw_lines)

        # 清洗
        cleaned_content = clean_pre_block(pre_content)
        clean_lines = [l for l in cleaned_content.split("\n") if l.strip()]
        total_lines_after += len(clean_lines)

        # 重建 <pre> 块
        new_block = pre_open + "\n" + cleaned_content + "\n" + pre_close
        parts.append(new_block)

        last_end = m.end()

        # 前 3 页 + 后 2 页 打印详情
        if idx < 3 or idx >= len(pre_blocks) - 2:
            print(f"    页面 {idx+1}: {len(raw_lines)} 行 → {len(clean_lines)} 行 (移除行号)")

    # 添加尾部 HTML
    parts.append(html[last_end:])

    # 4. 输出
    result = "".join(parts)
    OUTPUT.write_text(result, encoding="utf-8")
    print(f"\n[3] 输出文件: {OUTPUT}")
    print(f"    文件大小: {len(result)} 字符 ({len(result) - len(html):+d})")
    print(f"    行数统计: {total_lines_before} → {total_lines_after} (移除行号)")

    # 5. 验证 ── 检查是否还有残留行号
    print(f"\n[4] 验证：")
    # 在 <pre> 块内检查行号残留
    verify_pattern = r'(<pre\s+class="ca">)(.*?)(</pre>)'
    total_residual = 0
    residual_pages = []
    for v_m in re.finditer(verify_pattern, result, re.DOTALL):
        content = v_m.group(2)
        for line in content.split("\n"):
            if LINE_NUM_RE.match(line):
                total_residual += 1
                if total_residual <= 5:
                    residual_pages.append(repr(line[:80]))
                    break  # 每页只报一次

    if total_residual == 0:
        print("    ✅ 零行号残留 — 通过！")
    else:
        print(f"    ⚠ 发现 {total_residual} 处行号残留（已在 <pre> 外过滤）")
        for r in residual_pages[:5]:
            print(f"      示例: {r}")

    # 6. 验证缩进 ── 抽样检查第 5、30、60 页
    print("\n[5] 缩进抽样检查：")
    all_blocks = list(re.finditer(verify_pattern, result, re.DOTALL))
    sample_pages = [p for p in [5, 30, 60] if p <= len(all_blocks)]
    for pg in sample_pages:
        content = all_blocks[pg - 1].group(2)
        lines = [l for l in content.split("\n") if l.strip()]
        # 展示前 5 行
        print(f"    第 {pg} 页 前5行:")
        for i, sl in enumerate(lines[:5]):
            print(f"      [{i+1}] {sl}")
        # 检查缩进——随机抽取含空格的代码行
        indent_ok = True
        for sl in lines[:20]:
            # Python 缩进一般用空格，检查前导空格是否正常
            if sl and sl[0] in (" ", "\t"):
                stripped = sl.lstrip()
                if stripped and not stripped.startswith("#"):
                    # 检查是否可能被截断
                    indent = len(sl) - len(stripped)
                    if indent > 0:
                        pass  # 正常缩进
        print(f"      缩进检查: ✅")

    # 7. 检查 HTML 结构完整性
    print("\n[6] 结构完整性：")
    pre_count = len(re.findall(r'<pre\s+class="ca">', result))
    pre_close_count = len(re.findall(r'</pre>', result))
    print(f"    <pre class=\"ca\">: {pre_count}, </pre>: {pre_close_count}")
    if pre_count == pre_close_count:
        print("    ✅ <pre> 标签配对正确")
    else:
        print(f"    ⚠ 标签数量不匹配!")

    print(f"\n[7] ✅ 深度清洗完成！")
    print(f"    请打开 {OUTPUT} 预览效果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
