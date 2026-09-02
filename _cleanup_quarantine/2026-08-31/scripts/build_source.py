# -*- coding: utf-8 -*-
"""build_source.py — 纯净版：白名单驱动，无拼接痕迹，流式输出"""
import pathlib


FILES = [
    "backend/app/api/v1/endpoints/tasks.py",
    "backend/app/api/v1/endpoints/traces.py",
    "backend/app/api/v1/endpoints/experiments.py",
    "backend/app/api/v1/endpoints/reports.py",
    "backend/app/api/v1/endpoints/ab.py",
    "backend/app/api/v1/endpoints/agents_http.py",
    "backend/app/api/v1/endpoints/audit.py",
    "backend/app/api/v1/endpoints/benchmarks.py",
    "backend/app/api/v1/endpoints/billing.py",
    "backend/app/api/v1/endpoints/dashboard.py",
    "backend/app/api/v1/endpoints/diagnosis.py",
    "backend/app/api/v1/endpoints/judges.py",
    "backend/app/api/v1/endpoints/logs.py",
    "backend/app/api/v1/endpoints/me.py",
    "backend/app/api/v1/endpoints/media.py",
    "backend/app/api/v1/endpoints/observability.py",
    "backend/app/api/v1/endpoints/plugins.py",
    "backend/app/api/v1/endpoints/settings.py",
    "backend/app/api/v1/endpoints/tenants.py",
    "backend/app/api/v1/endpoints/tools.py",
    "backend/app/api/v1/endpoints/ws.py",
    "backend/app/api/v1/router.py",
    "backend/app/models/task.py",
    "backend/app/models/trace.py",
    "backend/app/models/metric_score.py",
    "backend/app/models/experiment.py",
    "backend/app/models/ab_test.py",
    "backend/app/models/agent_log.py",
    "backend/app/models/audit_log.py",
    "backend/app/models/base.py",
    "backend/app/models/benchmark.py",
    "backend/app/models/billing.py",
    "backend/app/models/media_asset.py",
    "backend/app/models/slow_task.py",
    "backend/app/models/tenant.py",
    "backend/app/core/security.py",
    "backend/app/core/tenancy.py",
    "backend/app/core/middleware.py",
    "backend/app/core/rbac.py",
    "backend/app/core/audit.py",
    "backend/app/core/events.py",
    "backend/app/core/ws_hub.py",
    "backend/app/core/ab/assignment.py",
    "backend/app/core/ab/service.py",
    "backend/app/core/ab/stats.py",
    "backend/app/core/agent_runner/base.py",
    "backend/app/core/agent_runner/factory.py",
    "backend/app/core/agent_runner/openai_runner.py",
    "backend/app/core/agent_runner/http_runner.py",
    "backend/app/core/agent_runner/parser.py",
    "backend/app/core/agent_runner/protocol.py",
    "backend/app/core/agent_runner/ssrf.py",
    "backend/app/core/agent_runner/tool_sandbox.py",
    "backend/app/core/judge_engine/base.py",
    "backend/app/core/judge_engine/llm_judge.py",
    "backend/app/core/judge_engine/metrics.py",
    "backend/app/core/judge_engine/scorecard.py",
    "backend/app/core/evaluation/pipeline.py",
    "backend/app/core/evaluation/compare.py",
    "backend/app/core/celery_app/celery.py",
    "backend/app/core/celery_app/tasks.py",
    "backend/app/core/resilience/circuit_breaker.py",
    "backend/app/core/resilience/policy.py",
    "backend/app/core/resilience/retry.py",
    "backend/app/core/resilience/timeout.py",
    "backend/app/core/diagnosis/engine.py",
    "backend/app/core/plugins/base.py",
    "backend/app/core/plugins/loader.py",
    "backend/app/core/plugins/manager.py",
    "backend/app/core/plugins/registry.py",
    "backend/app/core/plugins/sandbox.py",
    "backend/app/core/plugins/signature.py",
    "backend/app/core/observability/metrics.py",
    "backend/app/core/observability/tracing.py",
    "backend/app/core/observability/timeseries.py",
    "backend/app/core/observability/aols/events.py",
    "backend/app/core/observability/aols/emit.py",
    "backend/app/schemas/experiment.py",
    "backend/app/schemas/task.py",
    "backend/app/schemas/trace.py",
]

ROOT = pathlib.Path(r"D:\AgentFlow-Eval")
OUT_TXT = ROOT / "source_code_60pages.txt"

SKIP_EXACT = {
    "# AgentFlow-Eval V1", "# === File:", "(c) 2026", "Author:",
    "!/usr/bin/env", "# -*- coding:", "from __future__",
}

def should_skip(line: str, in_header: bool) -> bool:
    s = line.strip()
    if s == "": return True
    if in_header and s.startswith("#"):
        if len(s) < 3: return True
        for pat in SKIP_EXACT:
            if pat in s: return True
        if s.startswith('"""') or s.startswith("'''"): return True
        if s in ("#", "##"): return True
    return False

def stream_file(rel, out):
    fp = ROOT / rel
    if not fp.exists(): return 0
    try:
        raw = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    lines = raw.split("\n")
    in_header = True
    written = 0
    for line in lines:
        l = line.rstrip("\r")
        if in_header:
            s = l.strip()
            if s and not s.startswith("#") and not s.startswith('"') and not s.startswith("'"):
                in_header = False
        if should_skip(l, in_header): continue
        out.write(l + "\n")
        written += 1
    if written > 0: out.write("\n")
    return 1

def build():
    out = open(str(OUT_TXT), "w", encoding="utf-8")
    ok = 0
    for rel in FILES:
        ok += stream_file(rel, out)
    out.close()
    with open(str(OUT_TXT), "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    eff = sum(1 for l in all_lines if l.strip())
    print(f"[OK] {ok}/{len(FILES)} files, {len(all_lines)} lines ({eff} effective)")
build()
