# -*- coding: utf-8 -*-
"""软著·源程序鉴别材料生成器（前后各30页 / 每页50行 / 含装订线）"""
import html, shutil
from pathlib import Path

# ============ 可调常量（所有"旋钮"都在这，别处不用动） ============
PROJECT_NAME      = "AgentFlow-Eval"
VERSION           = "V1.0"
AUTHOR            = "LiKaixin"          # 文件标记行里的作者
COPYRIGHT_HOLDER  = "李凯昕"             # 版权块里的著作权人
SUBMIT_DATE       = "2026-07-28"
HEADER_TITLE      = f"{PROJECT_NAME} 源程序鉴别材料 {VERSION}"   # 页眉（想跟截图一样只留产品名就改成 f"{PROJECT_NAME} {VERSION}"）
PRODUCT_LINE      = f"{PROJECT_NAME} {VERSION}"                  # 版权块第二行

LINES_PER_PAGE    = 50     # 每页严格50行
FRONT_PAGES       = 30     # 前30页
BACK_PAGES        = 30     # 后30页
FILE_FULL_THRESH  = 60     # 单文件 <= 此行数 -> 全文展示
FILE_HEAD         = 25     # 超长文件保留头部行数
FILE_TAIL         = 25     # 超长文件保留尾部行数

EXCLUDE_DIRS = {".venv","venv","__pycache__",".git","node_modules","build",
                "dist",".tox",".mypy_cache",".pytest_cache","htmlcov",
                "tests","test",".idea",".vscode"}

OMIT = [  # 文件内省略标记（3行，与你旧版一致）
    "# ============================================================",
    "# （此处省略中间部分源代码）",
    "# ============================================================",
]
COPYRIGHT_BLOCK = [  # 首页版权块（© 是按软著惯例补的；不要就把这行的 © 删掉）
    "# ============================================================",
    f"# {PRODUCT_LINE}",
    f"# 版权所有 © 2026 {COPYRIGHT_HOLDER}",
    f"# 提交日期: {SUBMIT_DATE}",
    "# ============================================================",
    "",
]

CSS = """
@page { size: A4 portrait; margin: 0; }
* { box-sizing: border-box; margin:0; padding:0; }
html,body { background:#fff; }
.page {
  position: relative; width: 210mm; height: 297mm;
  padding: 15mm 12mm 12mm 25mm;          /* 左25mm = 装订线 */
  page-break-after: always; overflow: hidden;
}
.page:last-child { page-break-after: auto; }
.header {
  height: 9mm; line-height: 9mm; text-align: center;
  font: 600 12pt/9mm "SimSun","宋体",serif;
  border-bottom: 1.5px solid #000; margin-bottom: 3mm;   /* 截图那条横线 */
}
.body { height: 240mm; overflow: hidden; }               /* 50 * 4.8mm */
.line {
  height: 4.8mm; line-height: 4.8mm;                     /* 固定行高=一个槽 */
  font: 9pt/4.8mm Consolas,"Courier New","DejaVu Sans Mono",monospace;
  white-space: pre; overflow: hidden; color:#000;        /* 不折行，长行截断 */
}
.footer {
  position:absolute; left:25mm; right:12mm; bottom:5mm;
  height:7mm; line-height:7mm; text-align:center;
  font: 9pt/7mm "SimSun","宋体",serif;
}
@media screen { body{background:#888;} .page{margin:10mm auto; box-shadow:0 0 6mm #000;} }
"""

# ============ 路径 ============
ROOT     = Path(__file__).resolve().parents[2]          # 项目根
BACKEND  = ROOT / "backend"
OUT_HTML = ROOT / "docs" / "soft-copyright" / "源程序鉴别材料.html"
OUT_PDF  = ROOT / "docs" / "soft-copyright" / "generated" / "源程序鉴别材料_AgentFlow-Eval_V1.0.pdf"

# ============ 1. 收集文件（按相对路径字母序，与你旧版一致） ============
files = []
for p in sorted(BACKEND.rglob("*.py")):
    rel = p.relative_to(BACKEND)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        continue
    files.append((rel.as_posix(), p))

# ============ 2. 构造行流 ============
stream = list(COPYRIGHT_BLOCK)
for rel, p in files:
    try:
        src_lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        src_lines = []
    stream.append(f"# === File: {rel} === | Author: {AUTHOR}")
    if len(src_lines) <= FILE_FULL_THRESH:
        stream.extend(src_lines)
    else:
        stream.extend(src_lines[:FILE_HEAD])
        stream.extend(OMIT)
        stream.extend(src_lines[-FILE_TAIL:])

# ============ 3. 边界对齐辅助 ============
def _find_boundary_backward(lines: list[str], cut: int, search: int = 120) -> int:
    """从 cut 位置向前搜索最近的段落边界。
       优先级：空行后跟非缩进代码 > 文件标记行 > 空行后跟 def/class。"""
    # 第 1 轮：找空行 + 后续非缩进代码（段落边界）
    for i in range(cut - 1, max(0, cut - search), -1):
        stripped = lines[i].strip()
        if stripped != "":
            continue
        for j in range(i + 1, min(len(lines), i + 4)):
            sj = lines[j].strip()
            if sj == "":
                continue
            if sj.startswith("# === File:"):
                # 文件标记行 → 理想的边界
                return i
            if not sj.startswith((" ", "\t")) and not sj.startswith("#"):
                prev = lines[i - 1].strip() if i > 0 else ""
                if prev and prev[0] in ")]}:\\":
                    break  # 延续行，跳过
                return i
            break
    # 第 2 轮：直接找文件标记行前的空行
    for i in range(cut - 1, max(0, cut - search), -1):
        if lines[i].strip().startswith("# === File:"):
            return i - 1  # 文件标记行前一行为边界
    return cut

def _find_boundary_forward(lines: list[str], start: int, search: int = 80) -> int:
    """从 start 位置向后搜索最近的段落开头（非缩进行，如 def/class/file-header）。"""
    for i in range(start, min(len(lines), start + search)):
        raw = lines[i]
        s = raw.strip()
        if s == "":
            continue
        # File header or class/def → ideal paragraph start
        if s.startswith("# === File:") or s.startswith("class ") or s.startswith("def "):
            return i
        # 跳过：缩进代码、注释、装饰器、延续行、字符串字面量
        if raw and raw[0] in (" ", "\t", "#", "@", ")", "]", "}", ":", "\"", "'"):
            continue
        # 非缩进、非跳过 → 新段落开始
        return i
    return start  # 未找到，返回原位置

# ============ 4. 取 前30页 + 后30页（不足60页则全交，合规） ============
need = (FRONT_PAGES + BACK_PAGES) * LINES_PER_PAGE      # 3000
front_lines = FRONT_PAGES * LINES_PER_PAGE               # 1500
back_lines  = BACK_PAGES * LINES_PER_PAGE                # 1500

if len(stream) <= need:
    show = stream
else:
    # 前段：回退到最近的段落边界（文件标记或段落空行）
    boundary = _find_boundary_backward(stream, front_lines)
    actual_front = boundary + 1 if boundary < front_lines else front_lines

    # 后段：向前对齐到段开头（def/class/file-header）
    back_target = need - actual_front
    back_start = len(stream) - back_target
    aligned_start = _find_boundary_forward(stream, back_start)

    # 最终确认总行数 = need
    actual_back = len(stream) - aligned_start
    if actual_front + actual_back < need:
        # 前后段总和不足 → 扩大后段（向前多取）
        aligned_start = len(stream) - (need - actual_front)
    elif actual_front + actual_back > need:
        # 前后段总和超出 → 收缩后段
        aligned_start = len(stream) - (need - actual_front)

    show = stream[:actual_front] + stream[aligned_start:]
    actual_back = len(stream) - aligned_start
    if actual_front != front_lines or actual_back != back_lines:
        print(f"[INFO] 边界对齐: 前段 {front_lines}→{actual_front}, "
              f"后段 {back_lines}→{actual_back}  (总计 {len(show)})")

pages = [show[i:i + LINES_PER_PAGE] for i in range(0, len(show), LINES_PER_PAGE)]
for pg in pages:                                        # 每页补空槽到50
    while len(pg) < LINES_PER_PAGE:
        pg.append("")
N = len(pages)

# ============ 4. 渲染 HTML ============
def esc(s): return html.escape(s, quote=False)

parts = [f"<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
         f"<title>{esc(HEADER_TITLE)}</title><style>{CSS}</style></head><body>"]
for idx, pg in enumerate(pages, 1):
    lines_html = "".join(f"<div class='line'>{esc(x)}</div>" for x in pg)
    parts.append(
        f"<div class='page'>"
        f"<div class='header'>{esc(HEADER_TITLE)}</div>"
        f"<div class='body'>{lines_html}</div>"
        f"<div class='footer'>第 {idx}页/共 {N}页</div>"
        f"</div>"
    )
parts.append("</body></html>")
OUT_HTML.write_text("".join(parts), encoding="utf-8")

# ============ 5. 可选：自动转 PDF（playwright 可用时） ============
pdf_msg = ""
try:
    from playwright.sync_api import sync_playwright
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PDF.exists():                                # 备份旧 PDF，防覆盖丢失
        shutil.copy2(OUT_PDF, OUT_PDF.with_suffix(".bak.pdf"))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page()
        page.goto(OUT_HTML.as_uri())
        page.pdf(path=str(OUT_PDF), format="A4", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                 prefer_css_page_size=True)
        b.close()
    pdf_msg = f"[OK] PDF 已生成: {OUT_PDF}"
except Exception as e:
    pdf_msg = (f"[提示] 未自动生成PDF（playwright 不可用: {e}）。请手动: "
               f"Chrome 打开 {OUT_HTML} -> 打印 -> 纸张A4 -> 边距选'无' -> "
               f"勾选'背景图形' -> 缩放100% -> 另存为PDF")

# ============ 6. 自检输出 ============
print(f"[OK] HTML 已生成: {OUT_HTML}")
print(pdf_msg)
print(f"统计: 文件 {len(files)} 个 | 行流 {len(stream)} 行 | 展示 {len(show)} 行 | 共 {N} 页")
print(f"自检: 每页行数={LINES_PER_PAGE} | 装订线=左25mm | 行号=无 | 目录页=无 | 文件标记=B格式(无#(c))")
