#!/usr/bin/env python3
"""fix_copyright_final.py v4 - 修复逻辑断层、空白页、HTML转义"""
import re, sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
ORIG_HTML = HERE / "源程序鉴别材料.html"
OUTPUT    = HERE / "source_code_FINAL.html"
LPP = 50

RE_LN = re.compile(r"^\d{1,5}\s*\|\s*")
RE_MT = re.compile(r"^#\s*(={10,}|软件名称|版本号|著作权人|文件路径|"
                   r"功能描述|本文件代码行数|[©(c)\?]\s*\d{4}\s+)")

def strip_ln(s): return RE_LN.sub("", s, 1)
def is_mt(s): return bool(RE_MT.match(s.lstrip()))
def hd(s):
    return s.replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"').replace("&#39;","'").replace("&amp;","&")
def he(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def parse():
    """
    Extract all clean code lines from the original HTML.
    Strategy: read ALL lines from ALL pages, strip line numbers,
    skip metadata, HTML-decode. Return flat list of clean code lines.
    NO file boundary detection (avoids the cut-off header problem).
    """
    html = ORIG_HTML.read_text("utf-8")
    blocks = re.findall(r'<pre\s+class="ca">(.*?)</pre>', html, re.DOTALL)
    all_lines = []
    for content in blocks:
        for raw in content.split("\n"):
            line = strip_ln(raw)
            line = hd(line)  # HTML decode first
            stripped = line.strip()
            if is_mt(line): continue
            if not stripped: continue
            all_lines.append(line)
    return all_lines

def build_pages(lines):
    """Split lines into pages of exactly LPP lines. Last page may be shorter."""
    pages = []
    for i in range(0, len(lines), LPP):
        page = lines[i:i+LPP]
        pages.append(page)
    # Pad last page
    if pages:
        while len(pages[-1]) < LPP:
            pages[-1].append("")
    return pages

def gen_css(total_pages):
    if total_pages >= 60: lh = "1.4"
    elif total_pages >= 50: lh = "1.3"
    elif total_pages >= 40: lh = "1.2"
    elif total_pages >= 30: lh = "1.15"
    else: lh = "1.1"
    return rf"""@page{{size:A4 portrait;margin:18mm 16mm 16mm 16mm}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{font-family:'Courier New',Courier,monospace;font-size:9pt;color:#000;background:#fff}}
.pg{{display:flex;flex-direction:column;height:257mm;width:174mm;page-break-after:always;break-after:page;overflow:hidden}}
.pg:last-child{{page-break-after:auto}}
.hd{{display:flex;justify-content:space-between;align-items:baseline;padding-bottom:3mm;border-bottom:.5pt solid #333;margin-bottom:2mm;flex-shrink:0;font-size:9pt}}
.hd .l{{font-weight:bold}}
.ca{{flex:1 1 auto;margin:0;padding:0;overflow:hidden;font-family:'Courier New',Courier,monospace;font-size:9pt;line-height:{lh};white-space:pre;border:none;background:transparent}}
.ft{{text-align:center;padding-top:2mm;border-top:.5pt solid #999;margin-top:2mm;flex-shrink:0;font-size:8pt;color:#555}}
.tw{{padding:0}}
.tt{{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:6mm}}
.tm{{font-size:9pt;margin-bottom:5mm;line-height:1.8}}
.tm b{{display:inline-block;min-width:120pt}}
.tb{{width:100%;border-collapse:collapse;font-size:7.5pt}}
.tb th,.tb td{{border:.5pt solid #666;padding:2pt 3pt;text-align:left;vertical-align:top}}
.tb th{{background:#eee;font-weight:bold}}
.tb .c{{text-align:center}}
.tn{{font-size:8pt;margin-top:4mm;color:#333;line-height:1.5}}
@media print{{.pg{{page-break-after:always;break-after:page}}.pg:last-child{{page-break-after:auto}}}}"""

def gen_html(pages):
    css = gen_css(len(pages))
    hl, hr = "AgentFlow-Eval 源程序鉴别材料", "V1.0"
    h = ["<!DOCTYPE html>",'<html lang="zh-CN">','<head><meta charset="UTF-8">',
         "<title>AgentFlow-Eval 源程序鉴别材料</title>",f"<style>{css}</style></head><body>"]
    # TOC page (simple, no garbled paths)
    h.append('<div class="pg">')
    h.append(f'<div class="hd"><span class="l">{hl}</span><span class="r">{hr}</span></div>')
    h.append('<div class="tw"><div class="tt">AgentFlow-Eval 源程序鉴别材料 — 目录</div>')
    h.append('<div class="tm">')
    h.append("<b>软件名称：</b>AgentFlow-Eval<br>")
    h.append("<b>版本号：</b>V1.0<br>")
    h.append("<b>著作权人：</b>李凯昕<br>")
    h.append(f"<b>本文档代码页数：</b>{len(pages)}<br></div>")
    h.append("</div><div class=\"ft\">目录</div></div>")
    # Code pages
    for pi, pl in enumerate(pages, 1):
        h.append('<div class="pg">')
        h.append(f'<div class="hd"><span class="l">{hl}</span><span class="r">{hr}</span></div>')
        h.append('<pre class="ca">')
        for line in pl: h.append(he(line))
        h.append('</pre>')
        h.append(f'<div class="ft">第 {pi} 页 / 共 {len(pages)} 页</div></div>')
    h.append("</body></html>")
    return "\n".join(h)

def verify(pages):
    errs = []
    for pi, pg in enumerate(pages, 1):
        ne = [l for l in pg if l.strip()]
        if not ne: errs.append(f"Page {pi}: BLANK")
        for li, line in enumerate(pg):
            if RE_LN.match(line): errs.append(f"Page {pi}: line number"); break
        for li, line in enumerate(pg):
            if is_mt(line): errs.append(f"Page {pi}: metadata"); break
        for li, line in enumerate(pg):
            if "&amp;" in line: errs.append(f"Page {pi}: double-escaped"); break
    return errs

def show_transition(pages, pg_num, name_a, name_b):
    """Show last 3 lines of one page and first 3 of next."""
    if pg_num < len(pages):
        print(f"\n{name_a} (last 3):")
        for l in pages[pg_num-1][-3:]: print(f"  {l}")
    if pg_num < len(pages):
        print(f"{name_b} (first 3):")
        for l in pages[pg_num][:3]: print(f"  {l}")

def main():
    print("fix_copyright_final.py v4", flush=True)
    print("="*50, flush=True)
    lines = parse()
    print(f"Code lines: {len(lines)}", flush=True)
    pages = build_pages(lines)
    print(f"Pages: {len(pages)}", flush=True)
    html = gen_html(pages)
    OUTPUT.write_text(html, "utf-8")
    print(f"Output: {OUTPUT} ({len(html)} bytes)", flush=True)
    errs = verify(pages)
    if errs:
        print(f"\nFAIL ({len(errs)}):")
        for e in errs: print(f"  - {e}")
    else: print("\nALL PASS!", flush=True)
    show_transition(pages, 25, "Page 26", "Page 27")
    if len(pages) >= 2:
        show_transition(pages, len(pages)-1, "Last page", "")
    print(f"\n{'='*50}")
    print(f"Output: {OUTPUT}")
    return 0 if not errs else 1

if __name__ == "__main__":
    sys.exit(main())

