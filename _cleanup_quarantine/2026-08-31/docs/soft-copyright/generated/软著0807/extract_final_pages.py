#!/usr/bin/env python3
"""
Extract first 30 + last 30 pages from source_material.html (545 pages),
generating a compact 60-page HTML for final submission.
Ensures the end-of-model marker appears on the last page.
"""
import re
from pathlib import Path

BASE = Path(r"D:\AgentFlow-Eval\docs\soft-copyright\generated\软著0807")
SOURCE = BASE / "source_material.html"
OUTPUT = BASE / "FINAL_60_PAGES.html"
FRONT = 30
BACK = 30
NEW_TOTAL = FRONT + BACK  # 60
END_MARKER = "# === End of Task Model"


def main():
    print(f"Reading: {SOURCE}")
    html = SOURCE.read_text(encoding="utf-8")

    # Extract all <div class="page"> blocks
    page_pattern = re.compile(
        r'<div class="page">.*?</div>\s*(?=<div class="page">|</body>)',
        re.DOTALL,
    )
    pages = page_pattern.findall(html)
    total_original = len(pages)
    print(f"  Found {total_original} page blocks")

    # Find which page contains the end marker
    marker_page = -1
    for i, pg in enumerate(pages):
        if END_MARKER in pg:
            marker_page = i + 1  # 1-based
            print(f"  End marker found on original page {marker_page}")
            break

    if marker_page == -1:
        print("  WARNING: End marker not found in any page!")
        # Fallback: use last 30 pages
        back_start = total_original - BACK
    else:
        # Ensure marker is included: shift back range to include marker page
        # If marker is already in front 30 or back 30, we're fine
        # Otherwise, adjust back_start to include the marker page
        default_back_start = total_original - BACK
        if marker_page <= FRONT:
            # Marker is in front 30 - already covered
            back_start = default_back_start
            print(f"  Marker in front 30 (page {marker_page}), no adjustment needed")
        elif marker_page >= default_back_start + 1:
            # Marker is already in back 30 range
            back_start = default_back_start
            print(f"  Marker in back 30 (page {marker_page}), no adjustment needed")
        else:
            # Marker is in the middle - adjust back_start to include it
            back_start = marker_page - 1  # 0-based index
            # But we need exactly 30 pages, so shift back_start
            # back_start should be such that marker_page is within [back_start+1, back_start+BACK]
            back_start = max(0, marker_page - BACK)
            print(f"  Marker at page {marker_page}, adjusting back_start to {back_start + 1}")

    # Ensure we have exactly BACK pages
    back_start = max(0, back_start)
    back_start = min(back_start, total_original - BACK)

    # Extract front 30 (indices 0-29) and back 30
    front_pages = pages[:FRONT]
    back_pages = pages[back_start:back_start + BACK]

    print(f"  Front: pages 1-{FRONT}")
    print(f"  Back: pages {back_start + 1}-{back_start + BACK}")

    # Remap page numbers in footers
    new_pages = []
    for i, page_html in enumerate(front_pages):
        new_html = _update_footer(page_html, i + 1)
        new_pages.append(new_html)

    for i, page_html in enumerate(back_pages):
        new_html = _update_footer(page_html, FRONT + i + 1)
        new_pages.append(new_html)

    # Extract <head> section
    head_match = re.search(r"<head>.*?</head>", html, re.DOTALL)
    head_html = head_match.group(0) if head_match else "<head></head>"
    head_html = head_html.replace("counter(pages)", "60")

    # Build output
    output_parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        head_html,
        "<body>",
    ]
    output_parts.extend(new_pages)
    output_parts.append("</body>")
    output_parts.append("</html>")

    output_html = "\n".join(output_parts)
    OUTPUT.write_text(output_html, encoding="utf-8")

    # Verification
    verify_pages = page_pattern.findall(output_html)
    print(f"\nExtracted {len(verify_pages)} pages (front {FRONT} + back {BACK})")
    print(f"Saved: {OUTPUT}")

    first_footer = _extract_footer(verify_pages[0])
    last_footer = _extract_footer(verify_pages[-1])
    print(f"  第1页页脚: {first_footer}")
    print(f"  第60页页脚: {last_footer}")

    # Check end marker
    if END_MARKER in verify_pages[-1]:
        print(f"  ✅ 第60页包含封口注释: {END_MARKER} (完整单元) ===")
    else:
        # Check if marker is anywhere in the back pages
        for i, pg in enumerate(verify_pages[FRONT:]):
            if END_MARKER in pg:
                print(f"  ✅ 封口注释位于第{FRONT + i + 1}页: {END_MARKER}")
                break
        else:
            print(f"  ⚠️ 未在60页中找到封口注释，请手工确认")


def _update_footer(page_html: str, new_num: int) -> str:
    """Update page footer to reflect new page number and total 60."""
    return re.sub(
        r'(<div class="page-footer">)第\s*\d+\s*页\s*/\s*共\s*\d+\s*页(</div>)',
        rf'\1第 {new_num} 页 / 共 {NEW_TOTAL} 页\2',
        page_html,
    )


def _extract_footer(page_html: str) -> str:
    """Extract footer text from a page block."""
    m = re.search(
        r'<div class="page-footer">(.*?)</div>',
        page_html,
        re.DOTALL,
    )
    return m.group(1).strip() if m else "(no footer)"


if __name__ == "__main__":
    main()