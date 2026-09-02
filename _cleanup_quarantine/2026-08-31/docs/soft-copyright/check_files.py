#!/usr/bin/env python3
"""Check existence and line counts of the 28 required files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

FILES = [
    ("前段", "backend/app/main.py"),
    ("前段", "backend/app/core/middleware.py"),
    ("前段", "backend/app/core/plugins/manager.py"),
    ("前段", "backend/app/core/plugins/loader.py"),
    ("前段", "backend/app/core/plugins/registry.py"),
    ("前段", "backend/app/core/plugins/sandbox.py"),
    ("前段", "backend/app/core/plugins/signature.py"),
    ("前段", "backend/app/core/agent_runner/protocol.py"),
    ("前段", "backend/app/core/agent_runner/ssrf.py"),
    ("前段", "backend/app/core/agent_runner/base.py"),
    ("前段", "backend/app/core/judge_engine/base.py"),
    ("前段", "backend/app/core/judge_engine/llm_judge.py"),
    ("前段", "backend/app/core/ab/service.py"),
    ("后段", "backend/app/core/ab/assignment.py"),
    ("后段", "backend/app/core/ab/stats.py"),
    ("后段", "backend/app/core/resilience/circuit_breaker.py"),
    ("后段", "backend/app/core/resilience/retry.py"),
    ("后段", "backend/app/core/evaluation/pipeline.py"),
    ("后段", "backend/app/core/billing/service.py"),
    ("后段", "backend/app/core/rbac.py"),
    ("后段", "backend/app/core/security.py"),
    ("后段", "backend/app/core/tenancy.py"),
    ("后段", "backend/app/models/task.py"),
    ("后段", "backend/app/models/trace.py"),
    ("后段", "backend/app/models/experiment.py"),
    ("后段", "backend/app/schemas/task.py"),
    ("后段", "backend/app/schemas/experiment.py"),
    ("后段", "backend/app/core/plugins/hooks.py"),
]

missing = []
print(f"{'#':>3s} {'区域':4s} {'状态':5s} {'行数':>6s}  {'文件路径'}")
print("-" * 80)
total_lines = 0
for i, (section, fpath) in enumerate(FILES, 1):
    p = ROOT / fpath
    if p.exists():
        lines = p.read_text(encoding="utf-8").count("\n") + 1
        total_lines += lines
        print(f"{i:3d} {section:4s} OK       {lines:5d}  {fpath}")
    else:
        print(f"{i:3d} {section:4s} MISS         -  {fpath}")
        missing.append(fpath)

print("-" * 80)
print(f"  总计: {len(FILES)-len(missing)}/{len(FILES)} 个文件存在, {total_lines} 总行数")
if missing:
    print(f"\n  缺失 {len(missing)} 个文件:")
    for f in missing: print(f"    - {f}")
else:
    print(f"\n  全部 28 个文件存在！")
