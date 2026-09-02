"""Verify the cleaned output file."""
with open("docs/soft-copyright/source_code_clean.html", "r", encoding="utf-8") as f:
    html = f.read()

import re

blocks = re.findall(r'<pre class="ca">(.*?)</pre>', html, re.DOTALL)
print(f"Cleaned pre blocks: {len(blocks)}")
print()

# Show first few pages in detail
for idx in [0, 1, 2, 59]:
    content = blocks[idx]
    # Count lines in raw content
    lines = content.split("\n")
    print(f"Page {idx+1}: raw lines={len(lines)}, non-empty={sum(1 for l in lines if l.strip())}")
    print(f"  raw content repr: {repr(content[:200])}")
    print(f"  raw content (last): {repr(content[-100:])}")
    print()

# Check for line numbers  
all_content = "\n".join(html.split("<pre")[1:])  # everything inside pre blocks
line_num_count = len(re.findall(r"^\d{4,5} \| ", all_content, re.MULTILINE))
print(f"Line numbers remaining: {line_num_count}")

# Check for machine headers  
header_count = all_content.count("# 文件路径：")
print(f"File path headers remaining: {header_count}")

# Check real comment preserved
print(f"Real comment preserved: {'# parse .env.docker' in html}")

# Verify no copyright lines  
copyright_count = len(re.findall(r"#\s*\(c\)\s*\d{4}", html, re.IGNORECASE))
print(f"Copyright lines remaining: {copyright_count}")
