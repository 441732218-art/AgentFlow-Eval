# -*- coding: utf-8 -*-
"""Step3: 读取 trimmed_source.txt，按每50有效行分页，生成60页可打印HTML"""
import pathlib, html

SOFT_NAME = "AgentFlow-Eval"
VERSION   = "V1.0"

ROOT = pathlib.Path(r"D:\AgentFlow-Eval")
SRC  = ROOT / "source_code_60pages.txt"
OUT  = ROOT / "source_code_60pages.html"
EFFECTIVE_PER_PAGE = 50

def eff(s: str) -> bool:
    t = s.strip()
    return t != "" and not t.startswith("#")

def is_head(s: str) -> bool:
    return s.strip().startswith("# === File:")

def is_bar(s: str) -> bool:
    return s.strip().startswith("# ====")

def is_omit(s: str) -> bool:
    return "此处省略中间部分源代码" in s

lines = SRC.read_text(encoding="utf-8").splitlines()

# ---- 按有效行硬分页 ----
pages, cur, valid, i, n = [], [], 0, 0, len(lines)
while i < n:
    s = lines[i]
    if is_omit(s) and any(eff(x) for x in cur):
        pages.append(cur)
        cur, valid = [], 0
    cur.append(s)
    if eff(s):
        valid += 1
    i += 1
    if valid >= EFFECTIVE_PER_PAGE:
        absorbed = 0
        while i < n and absorbed < 4:
            ns = lines[i]
            if eff(ns) or is_omit(ns) or is_bar(ns) or is_head(ns):
                break
            cur.append(ns)
            i += 1
            absorbed += 1
        pages.append(cur)
        cur, valid = [], 0
if cur:
    pages.append(cur)

# ---- 校验 ----
valids = [sum(1 for x in p if eff(x)) for p in pages]
print(f"[INFO] 总页数: {len(pages)}")
print(f"[INFO] 每页有效行 min={min(valids)} max={max(valids)}")

# ---- 渲染 ----
N = len(pages)
CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Consolas, "Courier New", monospace; }
.page { width: 210mm; height: 297mm; padding: 14mm 12mm; margin: 0 auto;
        display: flex; flex-direction: column; page-break-after: always; }
.page:last-child { page-break-after: auto; }
.header { height: 8mm; line-height: 8mm; text-align: center;
          font-size: 11pt; font-weight: bold; border-bottom: 1px solid #000; }
.footer { height: 8mm; line-height: 8mm; text-align: center;
          font-size: 9pt; margin-top: auto; }
.code { flex: 1; margin: 2mm 0 0 0; font-size: 8pt; line-height: 1.15;
        white-space: pre; overflow: hidden; }
.omit { text-align: center; font-size: 14pt; padding: 4cm 0; color: #666; }
"""

parts = []
parts.append("<!DOCTYPE html>")
parts.append('<html lang="zh"><head><meta charset="utf-8">')
parts.append(f"<title>{SOFT_NAME} 源程序鉴别材料 {VERSION}</title>")
parts.append(f"<style>{CSS}</style></head><body>")

for k, p in enumerate(pages, 1):
    body = html.escape("\n".join(p))
    parts.append('<div class="page">')
    parts.append(f'<div class="header">{SOFT_NAME} 源程序鉴别材料 {VERSION}</div>')
    # Check if this is the omit page
    has_omit = any("此处省略中间部分源代码" in x for x in p)
    if has_omit:
        parts.append(f'<div class="omit"><p>—— 第 {k-1} 页之后省略中间部分源代码 ——</p><p>（前30页完，以下为后30页）</p></div>')
    else:
        parts.append(f'<pre class="code">{body}</pre>')
    parts.append(f'<div class="footer">第 {k} 页 / 共 {N} 页</div>')
    parts.append("</div>")

parts.append("</body></html>")

OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"[SAVED] -> {OUT}")
