#!/usr/bin/env python3
"""Diagnose current HTML state – page transitions, TOC issues, page count."""
import re
from pathlib import Path

HERE = Path(__file__).parent

# ── Load V2 (the latest cleaned version) ──
v2 = HERE / "source_code_FINAL_V2.html"
orig = HERE / "源程序鉴别材料.html"

# Actually load original to see the full picture with file boundaries
html = orig.read_text(encoding="utf-8")
blocks = list(re.finditer(r'(<pre\s+class="ca">)(.*?)(</pre>)', html, re.DOTALL))

print(f"Original HTML: {len(blocks)} <pre> blocks (pages)\n")

# ── Page 30-31 continuity ──
print("=" * 70)
print("  PAGE 30 → 31 TRANSITION (ORIGINAL)")
print("=" * 70)
if len(blocks) >= 31:
    content30 = blocks[29].group(2)
    lines30 = content30.split("\n")
    print(f"\n  Page 30 – last 10 lines:")
    for l in lines30[-10:]:
        stripped = re.sub(r"^\d{1,5}\s*\|\s*", "", l)
        print(f"    {stripped}")

    content31 = blocks[30].group(2)
    lines31 = content31.split("\n")
    print(f"\n  Page 31 – first 10 lines:")
    for l in lines31[:10]:
        stripped = re.sub(r"^\d{1,5}\s*\|\s*", "", l)
        print(f"    {stripped}")

# ── File boundaries ──
print("\n" + "=" * 70)
print("  FILE BOUNDARIES (look for // ===== FILE: markers)")
print("=" * 70)
file_markers = []
for pi, b in enumerate(blocks):
    content = b.group(2)
    for line in content.split("\n"):
        s = re.sub(r"^\d{1,5}\s*\|\s*", "", line).strip()
        if s.startswith("// ===== FILE:"):
            file_markers.append((pi + 1, s))

# Show which pages each file spans
current_file = None
file_pages = {}
for pg, marker in file_markers:
    fname = marker.split("FILE:")[-1].strip().rstrip("=").strip().rstrip()
    if current_file != fname:
        if current_file:
            file_pages[current_file]["end"] = pg - 1
        current_file = fname
        file_pages[fname] = {"start": pg, "end": pg}

if current_file:
    file_pages[current_file]["end"] = 60

for fname, pages in file_pages.items():
    print(f"  {fname:55s} 页 {pages['start']:2d} – {pages['end']:2d}")

# ── TOC issues in page 1 ──
print("\n" + "=" * 70)
print("  TABLE OF CONTENTS (look for garbled entries)")
print("=" * 70)
toc_section = html[:html.find('<div class="pg">', 1)]  # before first code page
# Find table rows
toc_rows = re.findall(r'<tr><td class="c">(\d+)</td><td>([^<]+)</td>', toc_section)
print(f"\n  TOC entries found: {len(toc_rows)}")
for idx, (num, path) in enumerate(toc_rows[:20]):
    marker = " ⚠️" if (" " in path.strip() and " " in path.replace("backend/", "", 1)) else ""
    print(f"    [{num}] {path}{marker}")

# ── Page count ──
print("\n" + "=" * 70)
print("  PAGE COUNT")
print("=" * 70)
# Count in original
print(f"  Original: {len(blocks)} pages (<pre> blocks)")

# Count in cleaned V2
v2_html = v2.read_text(encoding="utf-8")
v2_blocks = list(re.finditer(r'(<pre\s+class="ca">)(.*?)(</pre>)', v2_html, re.DOTALL))
print(f"  V2 (cleaned): {len(v2_blocks)} pages")

# ── Scan real project files ──
print("\n" + "=" * 70)
print("  REAL PROJECT SCAN (backend/*.py)")
print("=" * 70)
root = HERE.parent.parent / "backend"
excl = {"tests", "__pycache__", ".venv", "venv", "migrations", "alembic", "build", "dist", ".egg-info"}
py_files = []
for f in sorted(root.rglob("*.py")):
    rel = f.relative_to(HERE.parent.parent)
    parts = set(f.parts)
    if not excl & parts:
        py_files.append(str(rel.as_posix()))

print(f"  Found {len(py_files)} Python files")
for pf in py_files[:30]:
    print(f"    {pf}")
if len(py_files) > 30:
    print(f"    ... and {len(py_files)-30} more")

print(f"\n  Total: {len(py_files)} files")
