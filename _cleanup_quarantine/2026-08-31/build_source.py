#!/usr/bin/env python3
"""
build_source.py — 软著源代码文档生成器（轻量级流式处理版）

策略：
1. 显式文件白名单 — 不遍历目录，避免 I/O 超时
2. 逐行流式读取 & 清洗 — 不一次性加载所有内容到内存
3. 输出纯净 HTML — 无拼接痕迹，紧凑排版 60 页
"""

import os
from pathlib import Path

# ==================== CONFIGURATION ====================
ROOT_DIR = Path(r"D:\AgentFlow-Eval")
OUTPUT_RAW = ROOT_DIR / "raw_source.txt"
OUTPUT_HTML = ROOT_DIR / "source_code_60pages.html"

SOFTWARE_NAME = "AgentFlow 智能体评测管理平台软件"
VERSION = "V1.0"
# =======================================================

# ---------------------------------------------------------------------------
# 文件白名单（显式列出所有核心业务文件）
# 已排除：__init__.py, config.py, settings.py, 所有测试文件
# ---------------------------------------------------------------------------
WHITELIST = [
    # ---- API 路由 & 端点 ----
    "backend/app/main.py",
    "backend/app/api/v1/router.py",
    "backend/app/api/v1/endpoints/ab.py",
    "backend/app/api/v1/endpoints/agents_http.py",
    "backend/app/api/v1/endpoints/audit.py",
    "backend/app/api/v1/endpoints/benchmarks.py",
    "backend/app/api/v1/endpoints/billing.py",
    "backend/app/api/v1/endpoints/dashboard.py",
    "backend/app/api/v1/endpoints/diagnosis.py",
    "backend/app/api/v1/endpoints/experiments.py",
    "backend/app/api/v1/endpoints/judges.py",
    "backend/app/api/v1/endpoints/logs.py",
    "backend/app/api/v1/endpoints/me.py",
    "backend/app/api/v1/endpoints/media.py",
    "backend/app/api/v1/endpoints/observability.py",
    "backend/app/api/v1/endpoints/plugins.py",
    "backend/app/api/v1/endpoints/reports.py",
    "backend/app/api/v1/endpoints/tasks.py",
    "backend/app/api/v1/endpoints/tenants.py",
    "backend/app/api/v1/endpoints/tools.py",
    "backend/app/api/v1/endpoints/traces.py",
    "backend/app/api/v1/endpoints/ws.py",

    # ---- 核心业务模块 ----
    "backend/app/core/ab/assignment.py",
    "backend/app/core/ab/service.py",
    "backend/app/core/ab/stats.py",
    "backend/app/core/agent_runner/base.py",
    "backend/app/core/agent_runner/factory.py",
    "backend/app/core/agent_runner/http_runner.py",
    "backend/app/core/agent_runner/openai_runner.py",
    "backend/app/core/agent_runner/parser.py",
    "backend/app/core/agent_runner/protocol.py",
    "backend/app/core/agent_runner/ssrf.py",
    "backend/app/core/agent_runner/tool_sandbox.py",
    "backend/app/core/benchmark/service.py",
    "backend/app/core/billing/service.py",
    "backend/app/core/billing/stripe_checkout.py",
    "backend/app/core/cache/client.py",
    "backend/app/core/cache/decorators.py",
    "backend/app/core/cache/invalidation.py",
    "backend/app/core/cache/keys.py",
    "backend/app/core/cache/services.py",
    "backend/app/core/cache/warmup.py",
    "backend/app/core/celery_app/celery.py",
    "backend/app/core/celery_app/tasks.py",
    "backend/app/core/db/queries.py",
    "backend/app/core/diagnosis/engine.py",
    "backend/app/core/evaluation/compare.py",
    "backend/app/core/evaluation/pipeline.py",
    "backend/app/core/judge_engine/base.py",
    "backend/app/core/judge_engine/llm_judge.py",
    "backend/app/core/judge_engine/metrics.py",
    "backend/app/core/judge_engine/scorecard.py",
    "backend/app/core/multimodal/evaluator.py",
    "backend/app/core/multimodal/registry.py",
    "backend/app/core/multimodal/storage.py",
    "backend/app/core/multimodal/types.py",
    "backend/app/core/multimodal/extractors/image.py",
    "backend/app/core/multimodal/extractors/pdf.py",
    "backend/app/core/multimodal/extractors/spreadsheet.py",
    "backend/app/core/multimodal/extractors/text.py",
    "backend/app/core/observability/business_kpis.py",
    "backend/app/core/observability/metrics.py",
    "backend/app/core/observability/slow_tasks.py",
    "backend/app/core/observability/timeseries.py",
    "backend/app/core/observability/tracing.py",
    "backend/app/core/observability/aols/context.py",
    "backend/app/core/observability/aols/emit.py",
    "backend/app/core/observability/aols/events.py",
    "backend/app/core/observability/aols/logger.py",
    "backend/app/core/observability/aols/redaction.py",
    "backend/app/core/observability/aols/sinks/db.py",
    "backend/app/core/plugins/base.py",
    "backend/app/core/plugins/commerce.py",
    "backend/app/core/plugins/entitlement.py",
    "backend/app/core/plugins/hooks.py",
    "backend/app/core/plugins/loader.py",
    "backend/app/core/plugins/manager.py",
    "backend/app/core/plugins/market.py",
    "backend/app/core/plugins/registry.py",
    "backend/app/core/plugins/sandbox.py",
    "backend/app/core/plugins/signature.py",
    "backend/app/core/plugins/versioning.py",
    "backend/app/core/ports/cache.py",
    "backend/app/core/ports/event_bus.py",
    "backend/app/core/ports/metering.py",
    "backend/app/core/ports/task_queue.py",
    "backend/app/core/resilience/circuit_breaker.py",
    "backend/app/core/resilience/policy.py",
    "backend/app/core/resilience/retry.py",
    "backend/app/core/resilience/timeout.py",
    "backend/app/core/adapters/bus/inprocess.py",
    "backend/app/core/adapters/bus/redis_pubsub.py",
    "backend/app/core/adapters/cache/memory_only.py",
    "backend/app/core/adapters/cache/redis_l2.py",
    "backend/app/core/adapters/metering/noop.py",
    "backend/app/core/adapters/metering/sqlalchemy_meter.py",
    "backend/app/core/adapters/queue/celery_queue.py",
    "backend/app/core/adapters/queue/eager_queue.py",
    "backend/app/core/adapters/queue/memory_queue.py",
    "backend/app/core/audit.py",
    "backend/app/core/dependencies.py",
    "backend/app/core/events.py",
    "backend/app/core/middleware.py",
    "backend/app/core/rbac.py",
    "backend/app/core/security.py",
    "backend/app/core/seed.py",
    "backend/app/core/settings_guard.py",
    "backend/app/core/tenancy.py",
    "backend/app/core/tenant_context.py",
    "backend/app/core/ws_hub.py",
    "backend/app/models/ab_test.py",
    "backend/app/models/agent_log.py",
    "backend/app/models/audit_log.py",
    "backend/app/models/base.py",
    "backend/app/models/benchmark.py",
    "backend/app/models/billing.py",
    "backend/app/models/experiment.py",
    "backend/app/models/media_asset.py",
    "backend/app/models/metric_score.py",
    "backend/app/models/slow_task.py",
    "backend/app/models/task.py",
    "backend/app/models/tenant.py",
    "backend/app/models/test_suite.py",
    "backend/app/models/trace.py",
    "backend/app/schemas/ab_test.py",
    "backend/app/schemas/experiment.py",
    "backend/app/schemas/media.py",
    "backend/app/schemas/task.py",
    "backend/app/schemas/trace.py",
    "backend/app/plugins/examples/audit_hooks.py",
    "backend/app/plugins/examples/echo_runner.py",
    "backend/app/plugins/examples/echo_tool.py",
    "backend/app/plugins/examples/length_judge.py",
    "backend/app/utils/cost.py",
    "backend/app/utils/exceptions.py",
    "backend/app/utils/logger.py",
    "backend/app/cli/check_prod.py",
]

SKIP_KEYWORDS = ["=== File:", "(c) 2026", "Author:"]


def is_skip_line(line: str) -> bool:
    for kw in SKIP_KEYWORDS:
        if kw in line:
            return True
    return False


def is_doc_or_comment_or_decorator(stripped: str) -> bool:
    if not stripped:
        return True
    if stripped.startswith("#") or stripped.startswith("@"):
        return True
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    if stripped.startswith("from __future__"):
        return True
    return False


def process_one_file(abs_path: Path) -> list:
    """逐行处理单个文件，返回清洗后的行列表"""
    if not abs_path.exists():
        return []
    lines_out = []
    seen_code = False
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if is_skip_line(line):
                    continue
                stripped = line.strip()
                if not seen_code:
                    if is_doc_or_comment_or_decorator(stripped):
                        continue
                    seen_code = True
                if seen_code and stripped == "":
                    continue
                line = line.lstrip("\ufeff")  # strip BOM if present
                lines_out.append(line.rstrip("\n"))
    except Exception as e:
        print(f"  [WARN] {abs_path.name}: {e}")
        return []
    return lines_out



def main():
    os.chdir(str(ROOT_DIR))
    print(f"工作目录: {ROOT_DIR}")

    total = 0
    processed = 0
    with open(OUTPUT_RAW, "w", encoding="utf-8") as out:
        for rel_path in WHITELIST:
            abs_path = ROOT_DIR / rel_path
            clean_lines = process_one_file(abs_path)
            if not clean_lines:
                continue
            processed += 1
            for ln in clean_lines:
                out.write(ln + "\n")
                total += 1
            out.write("\n")
            print(f"  [OK] {rel_path}  ({len(clean_lines)} lines)")

    print(f"\n  raw_source.txt: {total} 行, {processed}/{len(WHITELIST)} 文件")

    with open(OUTPUT_RAW, "r", encoding="utf-8") as fh:
        all_lines = [line.rstrip("\n") for line in fh]

    pages = []
    LINES_PER_PAGE = 50
    for i in range(0, len(all_lines), LINES_PER_PAGE):
        pages.append(all_lines[i:i + LINES_PER_PAGE])
    total_pages = len(pages)

    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{SOFTWARE_NAME} {VERSION}</title>
<style>
@page{{size:A4 portrait;margin:16mm 10mm 16mm 10mm}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Courier New",Consolas,monospace;font-size:10pt;line-height:1.2;color:#000}}
.page{{page-break-after:always;min-height:255mm;padding:6mm 4mm;position:relative}}
.page:last-child{{page-break-after:auto}}
.header{{border-bottom:1px solid #000;padding-bottom:2px;margin-bottom:6px;
    display:flex;justify-content:space-between;font-weight:bold;font-size:10pt}}
.footer{{position:absolute;bottom:5mm;left:4mm;right:4mm;text-align:center;
    border-top:1px solid #ccc;padding-top:2px;font-size:8pt;color:#555}}
pre{{margin:0;white-space:pre-wrap;word-wrap:break-word;font-family:inherit;
    font-size:10pt;line-height:1.2}}
</style>
</head>
<body>
""")

    for idx, chunk in enumerate(pages):
        pn = idx + 1
        code = "\n".join(chunk)
        html_parts.append(f"""
<div class="page">
<div class="header">
<span>{SOFTWARE_NAME} {VERSION}</span>
<span>第{pn}页 / 共{total_pages}页</span>
</div>
<pre>{code}</pre>
<div class="footer">- {pn} -</div>
</div>
""")

    html_parts.append("\n</body>\n</html>")

    with open(OUTPUT_HTML, "w", encoding="utf-8") as fh:
        fh.write("".join(html_parts))

    size_kb = OUTPUT_HTML.stat().st_size / 1024
    print(f"\n[DONE] {OUTPUT_HTML}")
    print(f"  总页数: {total_pages}  总行数: {total}  大小: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()

