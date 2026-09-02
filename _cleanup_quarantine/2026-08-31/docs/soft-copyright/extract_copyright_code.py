#!/usr/bin/env python3
"""Soft copyright extraction - 28 files to 60 pages."""
import re, sys
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LPP, TP, HALF = 50, 60, 30
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

def read(fp):
    p = ROOT / fp
    if not p.exists(): return []
    return p.read_text(encoding="utf-8").split("\n")

def clean(lines):
    out, i = [], 0
    while i < len(lines):
        l = lines[i].rstrip().replace("\t","    ")
        if re.match(r'^\s*(print\s*\(|breakpoint\(\)|import pdb)', l): i+=1; continue
        if re.search(r'#\s*(TODO|FIXME|HACK)\b', l): i+=1; continue
        if l.strip().startswith("#"):
            bs = i
            while i < len(lines) and lines[i].strip().startswith("#"): i += 1
            if i - bs >= 3: continue
            i = bs
        if re.match(r'\s*__all__\s*=', l):
            while i < len(lines) and re.match(r'\s*["\'\(\[]', lines[i+1].strip()): i += 1
            i += 1; continue
        if re.search(r'(?i)(password|secret|token|api_key)\s*=\s*["\'][^"\']+', l):
            l = re.sub(r'(\s*=\s*["\'])[^"\']+(["\'])', r'\1REDACTED\2', l)
        out.append(l)
        i += 1
    while len(out) >= 2 and out[-1].strip() == "" and out[-2].strip() == "": out.pop()
    return out

def hdr(fp):
    fn = fp.split("/")[-1]
    mod = fp.replace("backend/","").replace("/"+fn,"")
    return [
        f"# === File: {fp} ===",
        f"# Module: {mod} | (c) {YR} {SW} | Author: {AUTHOR}",
        "# " + "=" * 68,
    ]

def eff(line):

def build():
    all_l = []
    for fp in FILES:
        code = clean(read(fp))
        if not code: continue
        all_l.extend(hdr(fp))
        all_l.extend(code)
    pages, pg, pe = [], [], 0
    for line in all_l:
        if eff(line):
            if pe >= LPP: pages.append(pg); pg = []; pe = 0
            pe += 1
        pg.append(line)
    if pg: pages.append(pg)
    for pg in pages:
        while sum(1 for l in pg if eff(l)) < LPP: pg.append("")
    fp = pages[:HALF]
    bp = pages[HALF:HALF*2] if len(pages) > HALF else []
    while len(bp) < HALF: bp.append([""]*LPP)
    return fp, bp

def output(fp, bp):
    pages = fp + bp
    o = [f"# {SW} Source Code Identification Materials",
         f"# {VER} | Author: {AUTHOR} | {YR}",
         f"# {len(pages)} pages (front {HALF} + back {HALF}) | {LPP} lines/page",
         "# " + "="*72, ""]
    for pi, pg in enumerate(pages, 1):
        o.append(f"{SW} Source Code Identification Materials {VER}")
        o.append("-"*60)
        o.extend(pg)

def main():
    print(f"  {SW} extraction", flush=True)
    missing = [f for f in FILES if not (ROOT/f).exists()]
    if missing:
        print(f"  MISSING: {len(missing)}")
        for f in missing: print(f"    {f}")
        return 1
    fp, bp = build()
    print(f"  Pages: {len(fp)}+{len(bp)}={len(fp)+len(bp)}", flush=True)
    txt = output(fp, bp)
    op = HERE / "source_code_final.txt"
    op.write_text(txt, encoding="utf-8", newline="\n")
    print(f"  Output: {op} ({len(txt):,} chars)", flush=True)
    for pi, pg in enumerate(fp+bp, 1):
        e = sum(1 for l in pg if eff(l))
        if e != LPP: print(f"  Page {pi}: {e} lines")
    print("\n  Done!", flush=True)

if __name__ == "__main__": main()

        o.append("-"*60)
        o.append(f"Page {pi} / {len(pages)}")
        o.append("")
    return "\n".join(o)

    s = line.strip()
    if not s or s.startswith("#"): return False
    return True

    "backend/app/schemas/task.py","backend/app/schemas/experiment.py",
    "backend/app/core/plugins/hooks.py",
]
