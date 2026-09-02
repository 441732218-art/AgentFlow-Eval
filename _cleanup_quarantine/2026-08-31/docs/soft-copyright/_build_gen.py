#!/usr/bin/env python3
"""Builds gen_copyright_doc.py by writing it in two passes."""
import os
D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "gen_copyright_doc.py")

# -- collect all priority file paths --
pf = []
pf += ["backend/app/main.py","backend/app/config.py"]
pf += ["backend/app/core/middleware.py","backend/app/core/security.py"]
pf += ["backend/app/core/rbac.py","backend/app/core/tenancy.py"]
pf += ["backend/app/core/tenant_context.py","backend/app/core/dependencies.py"]
pf += ["backend/app/core/seed.py","backend/app/core/settings_guard.py"]
pf += ["backend/app/core/events.py","backend/app/core/ws_hub.py"]
pf += ["backend/app/core/audit.py"]
pf += ["backend/app/models/"+x for x in ["base.py","task.py","trace.py","tenant.py",
     "billing.py","benchmark.py","experiment.py","metric_score.py","ab_test.py",
     "agent_log.py","audit_log.py","media_asset.py","slow_task.py"]]
pf += ["backend/app/api/v1/router.py"]
for x in ["tasks","traces","experiments","benchmarks","billing","dashboard",
          "diagnosis","reports","judges","agents_http","tenants","plugins",
          "tools","logs","media","ab","audit","me","observability","settings","ws"]:
    pf.append(f"backend/app/api/v1/endpoints/{x}.py")
pf += ["backend/app/core/evaluation/"+x for x in ["pipeline.py","compare.py"]]
pf += ["backend/app/core/judge_engine/"+x for x in ["base.py","llm_judge.py","scorecard.py","metrics.py"]]
pf += ["backend/app/core/agent_runner/"+x for x in ["base.py","openai_runner.py","http_runner.py",
     "factory.py","parser.py","protocol.py","ssrf.py","tool_sandbox.py"]]
for m in ["benchmark","billing","diagnosis"]:
    pf.append(f"backend/app/core/{m}/service.py" if m!="diagnosis" else f"backend/app/core/{m}/engine.py")
if "backend/app/core/billing/service.py" not in pf:
    pf.insert(pf.index("backend/app/core/billing/stripe_checkout.py") if "backend/app/core/billing/stripe_checkout.py" in pf else -1, "backend/app/core/billing/service.py")
pf += ["backend/app/core/billing/stripe_checkout.py"]
pf += ["backend/app/core/ab/"+x for x in ["service.py","assignment.py","stats.py"]]
pf += ["backend/app/core/cache/"+x for x in ["client.py","services.py","decorators.py","keys.py","invalidation.py","warmup.py"]]
pf += ["backend/app/core/resilience/"+x for x in ["retry.py","circuit_breaker.py","policy.py","timeout.py"]]
pf += ["backend/app/core/plugins/"+x for x in ["base.py","loader.py","manager.py","registry.py",
     "hooks.py","sandbox.py","signature.py","market.py","entitlement.py","commerce.py","versioning.py"]]
pf += ["backend/app/core/multimodal/"+x for x in ["evaluator.py","storage.py","types.py","registry.py"]]
pf += ["backend/app/core/multimodal/extractors/"+x for x in ["image.py","pdf.py","text.py","spreadsheet.py"]]
pf += ["backend/app/core/observability/"+x for x in ["metrics.py","tracing.py","business_kpis.py","timeseries.py","slow_tasks.py"]]
pf += ["backend/app/core/observability/aols/"+x for x in ["logger.py","emit.py","events.py","context.py","redaction.py"]]
pf += ["backend/app/core/observability/aols/sinks/db.py"]
pf += ["backend/app/core/celery_app/"+x for x in ["celery.py","tasks.py"]]
pf += ["backend/app/core/db/queries.py"]
pf += ["backend/app/core/ports/"+x for x in ["cache.py","event_bus.py","metering.py","task_queue.py"]]
pf += ["backend/app/core/adapters/bus/"+x for x in ["inprocess.py","redis_pubsub.py"]]
pf += ["backend/app/core/adapters/cache/"+x for x in ["memory_only.py","redis_l2.py"]]
pf += ["backend/app/core/adapters/metering/"+x for x in ["noop.py","sqlalchemy_meter.py"]]
pf += ["backend/app/core/adapters/queue/"+x for x in ["celery_queue.py","eager_queue.py","memory_queue.py"]]
pf += ["backend/app/schemas/"+x for x in ["task.py","trace.py","experiment.py","ab_test.py","media.py"]]
pf += ["backend/app/utils/"+x for x in ["logger.py","exceptions.py","cost.py"]]
pf += ["backend/app/cli/check_prod.py"]
pf += ["backend/app/plugins/examples/"+x for x in ["echo_runner.py","echo_tool.py","length_judge.py","audit_hooks.py"]]
pf += ["backend/app/core/profiles/__init__.py"]
# deduplicate preserving order
seen=set(); upf=[]
for p in pf:
    if p not in seen:
        seen.add(p); upf.append(p)
pf = upf
print(f"Collected {len(pf)} priority files")