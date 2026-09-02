#!/usr/bin/env python3
"""Analyze the current output for the three critical issues."""
import re
from pathlib import Path

data = (Path(__file__).parent / "source_code_FINAL_V2.html").read_text("utf-8")

# 1. Check page 26 (index 25) - file boundary issue
blocks = re.findall(r'<pre\s+class="ca">(.*?)</pre>', data, re.DOTALL)
print(f"Total pages: {len(blocks)}")
print()

# Check page 26 content
if len(blocks) >= 27:
    p26 = blocks[25].strip()
    lines26 = p26.split("\n")
    print(f"=== Page 26 ({len(lines26)} lines) ===")
    print("  FIRST 8:")
    for l in lines26[:8]: print(f"    {l[:90]}")
    print("  LAST 8:")
    for l in lines26[-8:]: print(f"    {l[:90]}")

if len(blocks) >= 26:
    p25 = blocks[24].strip()
    print(f"\n=== Page 25 (last 5) ===")
    for l in p25.split("\n")[-5:]: print(f"    {l[:90]}")

if len(blocks) >= 28:
    p27 = blocks[26].strip()
    print(f"\n=== Page 27 (first 5) ===")
    for l in p27.split("\n")[:5]: print(f"    {l[:90]}")

# 2. Check for blank pages
print(f"\n=== Blank page analysis ===")
for i, b in enumerate(blocks):
    content = b.strip().replace("\n", "")
    if not content or content.strip() == "":
        print(f"  Page {i+1}: EMPTY")
    elif len(set(content.split("\n"))) <= 2:
        lines = content.split("\n")
        non_empty = [l for l in lines if l.strip()]
        if not non_empty or all(l.strip() == "" for l in lines):
            print(f"  Page {i+1}: ALL BLANK")

# Check pages with mostly empty content
print(f"\n=== Pages with content analysis ===")
for i, b in enumerate(blocks):
    lines = b.strip().split("\n")
    non_empty = [l for l in lines if l.strip()]
    if len(non_empty) < 3 and i > 40:  # mostly empty pages in the back
        print(f"  Page {i+1}: {len(non_empty)} non-empty lines of {len(lines)}")
        for l in lines[:5]: print(f"    {l[:80]!r}")

# 3. Check HTML escaping issues
print(f"\n=== HTML escaping check ===")
amp_gt = data.count("&amp;gt;")
amp_lt = data.count("&amp;lt;")
amp_amp = data.count("&amp;amp;")
print(f"  &amp;gt; count: {amp_gt}")
print(f"  &amp;lt; count: {amp_lt}")
print(f"  &amp;amp; count: {amp_amp}")

# Samples
for pattern in ["&amp;gt;", "&amp;lt;", "&amp;amp;"]:
    idx = data.find(pattern)
    if idx >= 0:
        ctx = data[max(0,idx-20):idx+30]
        print(f"  Sample {pattern!r}: ...{ctx!r}...")
