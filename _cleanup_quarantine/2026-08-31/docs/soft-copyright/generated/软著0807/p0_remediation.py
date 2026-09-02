#!/usr/bin/env python3
"""P0 Remediation: fix FINAL_60_PAGES.html version headers, add filenames, clean junk."""
import re
from pathlib import Path

TARGET = Path(r"D:\AgentFlow-Eval\docs\soft-copyright\generated\软著0807\FINAL_60_PAGES.html")
HEADER_BASE = "AgentFlow-Eval Agent自动化评测工作台 V1.0"


def main():
    html = TARGET.read_text(encoding="utf-8")

    # P0-1: Replace V1.0 → V1.0
    html = html.replace(
        "<title>AgentFlow-Eval Agent自动化评测工作台 V1.0</title>",
        "<title>AgentFlow-Eval Agent自动化评测工作台 V1.0</title>",
    )
    c1 = html.count('AgentFlow-Eval Agent自动化评测工作台 V1.0</div>')
    html = html.replace(
        'AgentFlow-Eval Agent自动化评测工作台 V1.0</div>',
        'AgentFlow-Eval Agent自动化评测工作台 V1.0</div>',
    )

    # P0-2: Add filename to each page header
    page_re = re.compile(
        r'(<div class="page-header">)AgentFlow-Eval Agent自动化评测工作台 V1\.0\.0(</div>.*?<pre><code>\s*# === File: (.+?) ===)',
        re.DOTALL,
    )
    def add_filename(m):
        return f'{m.group(1)}{HEADER_BASE} \u2014 {m.group(3)}{m.group(2)}'
    html = page_re.sub(add_filename, html)
    c2 = len(re.findall(r'page-header">.*? \u2014 ', html))

    # P1-1: Remove #digit junk patterns
    def clean_code(m):
        inner = m.group(1)
        inner = re.sub(r'^\d[\d\s]{8,}$', '', inner, flags=re.MULTILINE)
        inner = re.sub(r'^#\s*\d[\d\s]{4,}\s*$', '', inner, flags=re.MULTILINE)
        return '<pre><code>' + inner + '</code></pre>'
    html = re.sub(r'<pre><code>(.*?)</code></pre>', clean_code, html, flags=re.DOTALL)

    TARGET.write_text(html, encoding="utf-8")

    # Verify
    final = TARGET.read_text(encoding="utf-8")
    print("=" * 50)
    print("P0/P1 FIX REPORT - FINAL_60_PAGES.html")
    print("=" * 50)
    print(f"[P0-1] V1.0 headers replaced: {c1} -> V1.0")
    print(f"[P0-2] Headers with filename: {c2}")
    print(f"[P0-1] Title: {'V1.0' if 'V1.0</title>' in final else 'CHECK!'}")

    pages = re.findall(r'<div class="page">.*?</div>\s*(?=<div class="page">|</body>)', final, re.DOTALL)
    print(f"[INFO] Total pages: {len(pages)}")

    # Check blank / low-eff pages
    for i, pg in enumerate(pages):
        cm = re.search(r'<pre><code>(.*?)</code></pre>', pg, re.DOTALL)
        if cm:
            lines = [l for l in cm.group(1).strip().split('\n') if l.strip() and not l.strip().startswith('#')]
            if len(lines) < 20:
                print(f"[P1-5] Page {i+1}: NEAR EMPTY ({len(lines)} lines)")
            elif len(lines) < 50:
                print(f"[P1-4] Page {i+1}: {len(lines)} effective lines (< 50)")

    print(f"\nFile: {TARGET}")


if __name__ == "__main__":
    main()