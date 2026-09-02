import re

INPUT = r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt"
OUTPUT = r"D:\AgentFlow-Eval\copyright_output\source_code_60pages_CLEANED.txt"
HOLDER = "李凯昕"

with open(INPUT, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Input: {len(lines)} lines")

cleaned = []
stats = {"author": 0, "omit": 0, "sep": 0, "bare_c": 0, "latex": 0}
in_omit = False

for i, line in enumerate(lines):
    s = line.rstrip("\n").rstrip("\r")

    if "此处省略中间部分源代码" in s:
        stats["omit"] += 1
        if cleaned and re.match(r'^#\s*=+\s*$', cleaned[-1].strip()):
            cleaned.pop()
            stats["sep"] += 1
        in_omit = True
        continue
    if in_omit and s.strip().startswith("#") and re.match(r'^#\s*=+\s*$', s.strip()):
        stats["sep"] += 1
        continue
    if in_omit and s.strip() == "":
        in_omit = False
        stats["sep"] += 1
        continue
    in_omit = False

    if "Author: LiKaixin" in s:
        s = re.sub(r'\s*\|\s*Author:\s*LiKaixin', '', s)
        stats["author"] += 1

    if re.match(r'^#\s*\(c\)\s+2026\s+AgentFlow-Eval\s*$', s.strip()):
        s = f"# (c) 2026 {HOLDER}"
        stats["bare_c"] += 1

    for m in re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_=<>!+\-*/%]*)\$', s):
        fixed = m
        fixed = fixed.replace("\\ge", ">=").replace("\\geq", ">=")
        fixed = fixed.replace("\\le", "<=").replace("\\leq", "<=")
        fixed = fixed.replace("\\ne", "!=").replace("\\neq", "!=")
        fixed = fixed.replace("\\times", "*").replace("\\div", "/")
        if fixed != m:
            s = s.replace(f"${m}$", fixed)
            stats["latex"] += 1
            print(f"  L{i+1}: ${m}$ -> {fixed}")

    if s.strip() == "" and cleaned and cleaned[-1].strip() == "":
        continue

    cleaned.append(s + "\n")

while cleaned and cleaned[-1].strip() == "":
    cleaned.pop()
cleaned.append("\n")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.writelines(cleaned)

print(f"Output: {len(cleaned)} lines")
for k, v in stats.items():
    print(f"  {k}: {v}")
print(f"Saved: {OUTPUT}")
