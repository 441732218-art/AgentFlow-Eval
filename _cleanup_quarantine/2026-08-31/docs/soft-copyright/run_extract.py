import re, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(r"d:\AgentFlow-Eval")
LPP = 50
SW = "AgentFlow-Eval"
VER = "V1.0"
AUTHOR = "Li Kaixin"
YR = datetime.now().strftime("%Y")

FILES = [
    "backend/app/main.py","backend/app/core/middleware.py",
    "backend/app/core/plugins/manager.py","backend/app/core/plugins/loader.py",
    "backend/app/core/plugins/registry.py","backend/app/core/plugins/sandbox.py",
    "backend/app/core/plugins/signature.py",
    "backend/app/core/agent_runner/protocol.py","backend/app/core/agent_runner/ssrf.py",
    "backend/app/core/agent_runner/base.py",
    "backend/app/core/judge_engine/base.py","backend/app/core/judge_engine/llm_judge.py",
    "backend/app/core/ab/service.py","backend/app/core/ab/assignment.py",
    "backend/app/core/ab/stats.py",
    "backend/app/core/resilience/circuit_breaker.py","backend/app/core/resilience/retry.py",
    "backend/app/core/evaluation/pipeline.py","backend/app/core/billing/service.py",
    "backend/app/core/rbac.py","backend/app/core/security.py",
    "backend/app/core/tenancy.py","backend/app/models/task.py",
    "backend/app/models/trace.py","backend/app/models/experiment.py",
    "backend/app/schemas/task.py","backend/app/schemas/experiment.py",
    "backend/app/core/plugins/hooks.py",
]

def file_header(fp):
    fn = fp.split("/")[-1]
    mod = fp.replace("backend/","").replace("/"+fn,"")
    return [
        f"# === File: {fp} ===",
        f"# Module: {mod} | (c) {YR} {SW} | Author: {AUTHOR}",
        "# " + "="*68,
    ]

def is_eff(line):
    s = line.strip()
    return bool(s) and not s.startswith("#")

all_lines = []
for fp in FILES:
    p = ROOT / fp
    if not p.exists():
        print(f"MISS: {fp}")
        continue
    raw = p.read_text(encoding="utf-8").split("\n")
    all_lines.extend(file_header(fp))
    for l in raw:
        l = l.rstrip().replace("\t","    ")
        if re.match(r"^\s*(print\s*\(|breakpoint\(\)|import pdb)", l): continue
        if re.search(r"#\s*(TODO|FIXME|HACK)", l): continue
        all_lines.append(l)

print(f"Total lines: {len(all_lines)}")

pages, pg, pe = [], [], 0
for line in all_lines:
    if is_eff(line):
        if pe >= LPP:
            pages.append(pg); pg = []; pe = 0
        pe += 1
    pg.append(line)
if pg:
    pages.append(pg)
for pg in pages:
    while sum(1 for l in pg if is_eff(l)) < LPP:
        pg.append("")

print(f"Pages: {len(pages)}")

out = [
    f"# {SW} Source Code Identification Materials",
    f"# {VER} | Author: {AUTHOR} | {YR}",
    f"# {len(pages)} pages (front 30 + back 30) | {LPP} lines/page",
    "# " + "="*72, ""
]
for pi, pg in enumerate(pages, 1):
    out.append(f"{SW} Source Code Identification Materials {VER}")
    out.append("-"*60)
    out.extend(pg)
    out.append("-"*60)
    out.append(f"Page {pi} / {len(pages)}")
    out.append("")

result = "\n".join(out)
op = Path("d:/AgentFlow-Eval/docs/soft-copyright/source_code_final.txt")
op.write_text(result, encoding="utf-8", newline="\n")
print(f"Output: {op} ({len(result):,} chars)")
