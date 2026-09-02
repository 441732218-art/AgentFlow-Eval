"""Diagnose the HTML structure - examine code blocks and header patterns."""
import re

with open("docs/soft-copyright/源程序鉴别材料.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all <pre class="ca"> blocks
blocks = re.findall(r'<pre class="ca">(.*?)</pre>', html, re.DOTALL)
print(f"Total code <pre> blocks: {len(blocks)}")
print()

# Show first block (page 1 code)
print("=== First pre block (first 15 lines) ===")
lines1 = blocks[0].strip().split("\n")
for i, ln in enumerate(lines1[:15]):
    print(f"  [{i+1:02d}] {repr(ln[:120])}")

print()
print("=== Second pre block (first 15 lines) ===")
lines2 = blocks[1].strip().split("\n")
for i, ln in enumerate(lines2[:15]):
    print(f"  [{i+1:02d}] {repr(ln[:120])}")

print()
print("=== Page 15 pre block (first 15 lines) ===")
lines15 = blocks[14].strip().split("\n")
for i, ln in enumerate(lines15[:15]):
    print(f"  [{i+1:02d}] {repr(ln[:120])}")

print()
print("=== Page 45 pre block (first 15 lines) ===")
lines45 = blocks[44].strip().split("\n")
for i, ln in enumerate(lines45[:15]):
    print(f"  [{i+1:02d}] {repr(ln[:120])}")

print()
print("=== Header comment pattern analysis ===")
# Check for the 8-line file header pattern
header_pattern = r"# ={77,}"
header_matches = re.finditer(header_pattern, html)
count = 0
for m in header_matches:
    count += 1
    start = max(0, m.start() - 10)
    end = min(len(html), m.end() + 200)
    snippet = html[start:end]
    print(f"\nHeader block #{count} (at pos {m.start()}):")
    print(f"  {repr(snippet[:260])}")
    if count >= 3:
        break

print()
print("=== Total header delimiter occurrences ===")
print(f"  Count: {len(re.findall(header_pattern, html))}")
