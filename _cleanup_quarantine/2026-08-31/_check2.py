"""Check the generated output."""
import re

with open("docs/soft-copyright/source_code_clean.html", "r", encoding="utf-8") as f:
    html = f.read()

blocks = []
pos = 0
while True:
    start = html.find('<pre class="ca">', pos)
    if start == -1:
        break
    end = html.find("</pre>", start)
    if end == -1:
        break
    blocks.append(html[start + len('<pre class="ca">') : end])
    pos = end + len("</pre>")

print(f"Blocks: {len(blocks)}")
for idx in [0, 1, 59]:
    c = blocks[idx]
    lines = c.split("\n")
    print(f"Page {idx+1}: raw={len(lines)}, nonempty={sum(1 for l in lines if l.strip())}")
    if idx == 0:
        print(f"  starts with empty: {lines[0] == ''}")
        print(f"  first: {repr(c[:120])}")
        print(f"  last: {repr(c[-80:])}")

total = sum(len(b.split("\n")) for b in blocks)
print(f"Total lines: {total}")

# Check line numbers
ln = len(re.findall(r"^\d{4,5} \| ", html, re.MULTILINE))
print(f"Line number patterns: {ln}")

# Check headers
hp = html.count("# 文件路径：")
print(f"File path headers: {hp}")
