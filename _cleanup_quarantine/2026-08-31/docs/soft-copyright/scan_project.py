#!/usr/bin/env python3
"""Scan project files for copyright extraction plan."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"
EXCL = {"tests","__pycache__",".venv","venv","migrations","alembic","build","dist",".egg-info","node_modules"}

files = []
for f in sorted(BACKEND.rglob("*.py")):
    if not EXCL & set(f.parts):
        rel = str(f.relative_to(ROOT).as_posix())
        try:
            lines = f.read_text(encoding="utf-8").split("\n")
            total = len(lines)
            non_empty = len([l for l in lines if l.strip()])
            non_comment = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
        except Exception:
            total = non_empty = non_comment = 0
        files.append((rel, total, non_empty, non_comment))

print(f"Total Python files: {len(files)}")
print(f"Total lines (all): {sum(f[1] for f in files)}")
print(f"Total non-empty lines: {sum(f[2] for f in files)}")
print(f"Total code lines: {sum(f[3] for f in files)}")

# 50 lines per page
pages_needed = sum(f[3] for f in files) / 50
print(f"Estimated pages: {pages_needed:.0f} (at 50 lines/page)")
print(f"Need front+back 60 pages: {'YES' if pages_needed >= 60 else 'NO'}")
print()

# Print every file
print(f"{'FILE':70s} {'TOTAL':>6s} {'CODE':>6s}")
print("-" * 85)
for rel, total, ne, nc in files:
    print(f"{rel:70s} {total:6d} {nc:6d}")
print("-" * 85)
print(f"{'TOTAL':70s} {sum(f[1] for f in files):6d} {sum(f[3] for f in files):6d}")

# Category breakdown
print("\n==== CATEGORY BREAKDOWN ====")
cats = {}
for rel, total, ne, nc in files:
    parts = rel.split("/")
    if len(parts) >= 2:
        cat = parts[1]  # "app" or "scripts"
        if cat == "app" and len(parts) >= 3:
            sub = parts[2]
            key = f"app/{sub}"
            if key not in cats: cats[key] = (0, 0)
            t, n = cats[key]
            cats[key] = (t + nc, n + 1)
        else:
            if cat not in cats: cats[cat] = (0, 0)
            t, n = cats[cat]
            cats[cat] = (t + nc, n + 1)

for k in sorted(cats.keys()):
    lines, count = cats[k]
    print(f"  {k:30s} {count:3d} files, {lines:5d} code lines")
