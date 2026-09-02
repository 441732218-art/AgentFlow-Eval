#!/usr/bin/env python3
"""Verify source_code_FINAL.html for all critical issues."""
import re
from pathlib import Path

data = (Path(__file__).parent / "source_code_FINAL.html").read_text("utf-8")
print(f"File size: {len(data)} bytes")

# Page count
blocks = re.findall(r'<pre\s+class="ca">(.*?)</pre>', data, re.DOTALL)
print(f"Total pages: {len(blocks)}")

# Check blank pages
blank = 0
for i, b in enumerate(blocks, 1):
    content = b.strip().replace("\n", "").replace(" ", "")
    if not content:
        print(f"  Page {i}: BLANK")
        blank += 1
print(f"Blank pages: {blank}")

# Check HTML double-escaping
amp_gt = data.count("&amp;gt;")
amp_lt = data.count("&amp;lt;")
amp_amp = data.count("&amp;amp;")
print(f"Double-escaped &amp;gt;: {amp_gt}")
print(f"Double-escaped &amp;lt;: {amp_lt}")
print(f"Double-escaped &amp;amp;: {amp_amp}")

# Check proper escaping (in code blocks)
proper_gt = data.count("&gt;")
proper_lt = data.count("&lt;")
print(f"Proper &gt; in HTML: {proper_gt}")
print(f"Proper &lt; in HTML: {proper_lt}")

# Check file boundary cleanliness
for i, b in enumerate(blocks, 1):
    lines = b.strip().split("\n")
    # Check that each FILE: marker starts clean
    for li, line in enumerate(lines):
        if "FILE:" in line and li > 0:
            prev = lines[li-1].strip()
            if prev and not prev.startswith("//"):
                print(f"  Page {i} L{li}: unclean file marker (prev={prev[:40]!r})")

print("\nDone.")
