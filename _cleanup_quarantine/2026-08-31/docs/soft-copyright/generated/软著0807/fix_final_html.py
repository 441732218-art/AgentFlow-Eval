#!/usr/bin/env python3
"""Fix FINAL_60_PAGES.html: remove @top-center/@bottom-center, ensure page-header on every page, strip leaked headers."""
import re
from pathlib import Path

TARGET = Path(r"D:\AgentFlow-Eval\docs\soft-copyright\generated\软著0807\FINAL_60_PAGES.html")
HEADER_TEXT = "AgentFlow-Eval Agent自动化评测工作台 V1.0"


def main():
    html = TARGET.read_text(encoding="utf-8")

    # === FIX 1: Strip @top-center and @bottom-center from @page rules ===
    # Remove @top-center { ... } blocks inside @page
    html = re.sub(
        r'@top-center\s*\{[^}]*\}',
        '',
        html,
        flags=re.DOTALL,
    )
    # Remove @bottom-center { ... } blocks inside @page
    html = re.sub(
        r'@bottom-center\s*\{[^}]*\}',
        '',
        html,
        flags=re.DOTALL,
    )
    # Clean up any double blank lines left behind
    html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)

    # === FIX 2: Ensure every <div class="page"> has a <div class="page-header"> ===
    page_pattern = re.compile(
        r'(<div class="page">)(.*?)(<div class="page-content">)',
        re.DOTALL,
    )

    def ensure_header(match):
        prefix = match.group(1)
        middle = match.group(2)
        suffix = match.group(3)
        if '<div class="page-header">' in middle:
            return match.group(0)  # already has header
        else:
            return (
                prefix
                + f'\n  <div class="page-header">{HEADER_TEXT}</div>\n'
                + suffix
            )

    html = page_pattern.sub(ensure_header, html)

    # === FIX 3: Remove any HEADER_TEXT that leaked inside <pre><code> blocks ===
    def strip_leaked_header(match):
        inner = match.group(1)
        # Remove standalone lines that are exactly the header text
        inner = re.sub(
            rf'^{re.escape(HEADER_TEXT)}\s*$',
            '',
            inner,
            flags=re.MULTILINE,
        )
        # Remove header text that got spliced into code lines
        inner = inner.replace(HEADER_TEXT, '')
        # Fix known corrupted line: "from app.core.plugins.sig" + header + "filter_signed_modules"
        inner = re.sub(
            r'from app\.core\.plugins\.sig\s+filter_signed_modules',
            'from app.core.plugins.signature import filter_signed_modules',
            inner,
        )
        return '<pre><code>' + inner + '</code></pre>'

    html = re.sub(
        r'<pre><code>(.*?)</code></pre>',
        strip_leaked_header,
        html,
        flags=re.DOTALL,
    )

    TARGET.write_text(html, encoding="utf-8")

    # === VERIFY ===
    final = TARGET.read_text(encoding="utf-8")

    # Check 1: No @top-center / @bottom-center
    tc = '@top-center' in final
    bc = '@bottom-center' in final
    print(f"[{'PASS' if not tc else 'FAIL'}] @top-center removed: {not tc}")
    print(f"[{'PASS' if not bc else 'FAIL'}] @bottom-center removed: {not bc}")

    # Check 2: All pages have header
    pages = re.findall(r'<div class="page">', final)
    headers = re.findall(r'<div class="page-header">', final)
    all_have = len(pages) == len(headers)
    print(f"[{'PASS' if all_have else 'FAIL'}] All {len(pages)} pages have header: {len(headers)} headers found")

    # Check 3: No header leaked in code blocks
    code_blocks = re.findall(r'<pre><code>(.*?)</code></pre>', final, re.DOTALL)
    leaked = sum(1 for b in code_blocks if HEADER_TEXT in b)
    print(f"[{'PASS' if leaked == 0 else 'FAIL'}] No header in code blocks: {leaked} leaked")

    # Check 4: First code line
    first_block = code_blocks[0] if code_blocks else ''
    first_line = first_block.strip().split('\n')[0].strip()
    is_main = '# === File: app/main.py ===' in first_line
    print(f"[{'PASS' if is_main else 'FAIL'}] Page 1 starts with app/main.py: {first_line[:60]}")

    print(f"\nDone! File: {TARGET}")


if __name__ == "__main__":
    main()