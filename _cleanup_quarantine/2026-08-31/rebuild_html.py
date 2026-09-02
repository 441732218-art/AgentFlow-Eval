#!/usr/bin/env python3
"""
rebuild_html.py — 软著源代码 HTML 生成器（合规版 v2）
修复: 1)打印隐藏非代码元素 2)版本统一V1.0 3)智能截断 4)脱敏
"""
import os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "raw_source.txt")
DST = os.path.join(ROOT, "AgentFlow_软著源代码_提交版_合规版.html")

FONT_SIZE = "9pt"
LINE_HEIGHT = "12.7pt"
LINES_PER_PAGE = 50
TOTAL_LINES = 3000
HALF = 1500
SOFTWARE_NAME = "AgentFlow-Eval Agent自动化评测工作台"
VERSION = "V1.0"

SANITIZE_PATTERNS = [
    (r'(mysql|postgresql|postgres|sqlite)://[^\s\'"]+', r'\1://YOUR_DATABASE_URL_HERE'),
    (r'(DATABASE_URL\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_DATABASE_URL_HERE\2'),
    (r'(API[_-]?KEY\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_API_KEY_HERE\2'),
    (r'(SECRET[_-]?KEY\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_SECRET_KEY_HERE\2'),
    (r'(STRIPE[_-]?SECRET\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_STRIPE_SECRET_HERE\2'),
    (r'(JWT[_-]?SECRET\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_JWT_SECRET_HERE\2'),
    (r'(PASSWORD\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_PASSWORD_HERE\2'),
    (r'(TOKEN\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_TOKEN_HERE\2'),
    (r'(REDIS_URL\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_REDIS_URL_HERE\2'),
    (r'(CELERY_BROKER_URL\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_CELERY_BROKER_URL_HERE\2'),
    (r'(API_SECRET\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_API_SECRET_HERE\2'),
    (r'(ACCESS_KEY\s*=\s*["\'])[^"\']+(["\"])', r'\1YOUR_ACCESS_KEY_HERE\2'),
    (r'([a-zA-Z0-9._%+-]+@)([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'email@\2'),
]


def find_boundary(lines, target, direction="forward"):
    """在 target 行附近 ±40 行内找空行边界"""
    for offset in range(0, 40):
        for sign in [1, -1] if direction == "forward" else [-1, 1]:
            i = target + sign * offset
            if 0 <= i < len(lines) and lines[i].strip() == "":
                return i
    return target


def sanitize(lines):
    new_lines, count = [], 0
    for line in lines:
        nl = line
        for pat, rep in SANITIZE_PATTERNS:
            c = len(re.findall(pat, nl, re.IGNORECASE))
            if c: nl = re.sub(pat, rep, nl, flags=re.IGNORECASE); count += c
        new_lines.append(nl)
    return new_lines, count


def unify_ver(lines):
    c = 0; nl = []
    for l in lines:
        if "1.0.0" in l: c += l.count("1.0.0"); l = l.replace("1.0.0", "1.0")
        nl.append(l)
    return nl, c


# ═══ 1. 读取 ═══
print("=" * 60)
print("[1/5] 读取 raw_source.txt ...")
with open(SRC, "r", encoding="utf-8") as f:
    all_lines = [l.rstrip("\n") for l in f]
print(f"  原始行数: {len(all_lines)}")

# 版本统一
all_lines, vc = unify_ver(all_lines)
print(f"  版本统一 (1.0.0→1.0): {vc} 处")

# 脱敏
all_lines, sc = sanitize(all_lines)
print(f"  脱敏替换: {sc} 处")

# ═══ 2. 智能截断 ═══
print(f"\n[2/5] 智能截断 (前30+后30页, {TOTAL_LINES}行) ...")
b1 = find_boundary(all_lines, HALF)
b2 = find_boundary(all_lines, len(all_lines) - HALF, "backward")
print(f"  前段边界: 行 {b1} (偏移 {b1-HALF:+d})")
print(f"  后段边界: 行 {b2} (偏移 {b2-(len(all_lines)-HALF):+d})")

front = all_lines[b1-HALF:b1] if b1 >= HALF else all_lines[:HALF]
back = all_lines[b2:b2+HALF] if b2+HALF <= len(all_lines) else all_lines[-HALF:]
if len(front) < HALF: front = all_lines[:HALF]
if len(back) < HALF: back = all_lines[-HALF:]
front, back = front[:HALF], back[:HALF]
final_lines = front + back
print(f"  前{len(front)}行 + 后{len(back)}行 = {len(final_lines)}行")


# ═══ 3. 生成 HTML ═══
print(f"\n[3/5] 生成 HTML ...")
pages = [final_lines[i:i+LINES_PER_PAGE] for i in range(0, len(final_lines), LINES_PER_PAGE)]
tp = len(pages)
print(f"  总页数: {tp}")

CSS_PRINT_HIDE = """        .ftr,
        .no-print,
        .file-path,
        .page-stats,
        .applicant-info,
        footer,
        .metadata,
        a[href^="file://"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -9999px !important;
        }"""

html_parts = [f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{SOFTWARE_NAME} {VERSION} 源程序鉴别材料</title>
<style>
    body {{ background: #e2e8f0; font-family: "Courier New",Consolas,"SimSun",monospace; margin: 0; padding: 20px; }}
    .page {{ width: 210mm; min-height: 297mm; margin: 0 auto 20px auto; background: #fff;
        box-shadow: 0 2px 12px rgba(0,0,0,.15); padding: 37mm 26mm 35mm 28mm;
        box-sizing: border-box; page-break-after: always; break-after: page; }}
    .page:last-child {{ page-break-after: auto; break-after: auto; }}
    .hdr {{ font-family: SimSun,"宋体",serif; font-size: 10pt; font-weight: bold;
        border-bottom: 0.5pt solid #222; padding-bottom: 2mm; margin-bottom: 3mm;
        display: flex; justify-content: space-between; }}
    .ftr {{ font-family: SimSun,"宋体",serif; font-size: 8pt; text-align: center;
        border-top: 0.4pt solid #888; padding-top: 2mm; margin-top: 3mm; color: #555; }}
    pre {{ margin: 0; white-space: pre-wrap; word-wrap: break-word;
        font-family: "Courier New",Consolas,"SimSun",monospace;
        font-size: {FONT_SIZE}; line-height: {LINE_HEIGHT}; color: #000; }}
    @media print {{
        @page {{ size: A4; margin: 37mm 26mm 35mm 28mm; }}
        body {{ background: #fff; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        .page {{ width: auto; min-height: auto; margin: 0; padding: 0; box-shadow: none;
            page-break-after: always; break-after: page; }}
        .page:last-child {{ page-break-after: auto; break-after: auto; }}
        pre {{ page-break-inside: avoid; break-inside: avoid; }}
{CSS_PRINT_HIDE}
    }}
</style>
</head>
<body>
''']

for idx, chunk in enumerate(pages):
    pn = idx + 1
    code_text = "\n".join(chunk)
    html_parts.append(f'''
<div class="page">
    <div class="hdr"><span>{SOFTWARE_NAME} {VERSION}</span><span>第 {pn} 页 / 共 {tp} 页</span></div>
    <pre>{code_text}</pre>
    <div class="ftr no-print applicant-info page-stats">本页 {len(chunk)} 行</div>
</div>''')

html_parts.append('\n</body>\n</html>')

with open(DST, "w", encoding="utf-8") as f:
    f.write("".join(html_parts))

size_kb = os.path.getsize(DST) / 1024

# ═══ 4. 脱敏自检 ═══
print(f"\n[4/5] 脱敏自检 ...")
LEAKS = [r'mysql://[^\s\'"]+', r'postgresql://[^\s\'"]+',
    r'API[_-]?KEY\s*=\s*["\'][A-Za-z0-9_\-]{8,}', r'SECRET\s*=\s*["\'][A-Za-z0-9_\-]{8,}',
    r'PASSWORD\s*=\s*["\'][A-Za-z0-9_\-]{4,}', r'TOKEN\s*=\s*["\'][A-Za-z0-9_\-]{8,}']
lc = 0
for p in LEAKS:
    m = re.findall(p, "\n".join(final_lines), re.IGNORECASE)
    if m: lc += len(m); print(f"  ⚠ {p[:50]}... — {len(m)}处")
if lc == 0: print(f"  ✅ 无敏感信息泄露")

# ═══ 5. 版本自检 ═══
print(f"\n[5/5] 版本一致性自检 ...")
v = "\n".join(final_lines).count("1.0.0")
if v: print(f"  ⚠ 仍有 {v} 处 '1.0.0'")
else: print(f"  ✅ 版本号已统一为 V1.0")

print(f"\n{'='*60}")
print(f"✅ 合规版 HTML: {DST}")
print(f"  大小:{size_kb:.1f}KB | 页数:{tp} | 行数:{len(final_lines)}")
print(f"  页脚(.ftr): 打印时彻底隐藏(9条CSS规则)")
print(f"  版本: {VERSION} | 脱敏: {sc}处")
print(f"{'='*60}")

