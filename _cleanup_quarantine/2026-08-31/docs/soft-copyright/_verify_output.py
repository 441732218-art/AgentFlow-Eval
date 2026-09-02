#!/usr/bin/env python3
"""Verify the output HTML."""
import re
from pathlib import Path

data = (Path(__file__).parent / "source_code_FINAL_V2.html").read_text(encoding="utf-8")
blocks = list(re.finditer(r'(<pre\s+class="ca">)(.*?)(</pre>)', data, re.DOTALL))
print(f"Pages: {len(blocks)}")
print()

RE_LINENO = re.compile(r"^\d{1,5}\s*\|\s*")
RE_META = re.compile(r"^#\s*(={10,}|软件名称|版本号|著作权人|文件路径|功能描述|本文件代码行数)")

if len(blocks) >= 31:
    lines30 = blocks[29].group(2).strip().split("\n")
    lines31 = blocks[30].group(2).strip().split("\n")
    print("=== Page 30 (last 8) ===")
    for l in lines30[-8:]:
        print(f"  {l}")
    print()
    print("=== Page 31 (first 8) ===")
    for l in lines31[:8]:
        print(f"  {l}")

lineno = meta = 0
for b in blocks:
    c = b.group(2)
    for line in c.split("\n"):
        if RE_LINENO.match(line):
            lineno += 1
        if RE_META.match(line.lstrip()):
            meta += 1

print()
print(f"Line number residues: {lineno}")
print(f"Meta comment residues: {meta}")

# Check each page line count
print()
all_ok = True
for i, b in enumerate(blocks, 1):
    lines = b.group(2).split("\n")
    if i <= 3 or i >= 58:
        print(f"  Page {i}: {len(lines)} lines")
    if len(lines) != 50:
        print(f"  *** Page {i} expects 50 lines, has {len(lines)}")
        all_ok = False

# Check TOC
toc_start = data.find("目录")
toc_end = data.find('<div class="pg">', 1)
toc_section = data[toc_start:toc_end] if toc_start > 0 else ""
print()
print(f"TOC section length: {len(toc_section)} chars")
# Find file entries
files_found = re.findall(r'<td>backend/[^<]+</td>', data[:blocks[0].start()])
print(f"Files in TOC: {len(files_found)}")
if all_ok:
    print("\nALL CHECKS PASSED!")
else:
    print("\nSOME CHECKS FAILED!")
