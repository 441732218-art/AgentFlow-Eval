# AgentFlow Intelligence v2.0 Development Roadmap

> **Companion to:** `docs/v2.0/01-v1-architecture-audit.md`  
> **Strategy:** Incremental Evolution â€?**new modules + compatibility**, never a v1 rewrite.  
> **v1.0 status:** Soft-copyright submitted. Treat as frozen baseline.  
> **This document does not authorize coding.** Wait for owner confirmation before Sprint 1.

---

## Product line

| Version | Theme | This document |
| --- | --- | --- |
| v1.0 | Agent Evaluation Workbench (frozen) | Audit only |
| **v2.0** | **Enterprise AI Agent Quality Platform** = Evaluation + Runtime | **In scope** |
| v3.0 | Enterprise Agent Governance | Out of scope (foundations only) |
| v4.0 | Vertical Agent Solutions | Out of scope |

v2.0 core capabilities (product, not a shopping list of models):

1. **Agent Runtime** â€?execute, state, (later) workflow, tool calls  
2. **Agent Evaluation** â€?quality scores, LLM Judge, benchmark, datasets  
3. **Observability foundation** â€?trace, LLM/tool, token, cost, latency  
4. **Security foundation** â€?keep v1 secret redaction / SSRF / RBAC; add agent/tool ACL seeds  

---

## Phase 0 â€?Architecture Audit

**Status: complete (this folder).**

| | |
| --- | --- |
| **Goal** | Map v1 real architecture; freeze change rules; design incremental v2 |
| **Tech** | Read-only code audit |
| **Files touched** | `docs/v2.0/01-v1-architecture-audit.md`, this file |
| **New modules** | None |
| **Risk** | None to product if no one starts coding on `main` |
| **Effort** | Done |

**Exit criteria:** Owner accepts audit + this roadmap.

---

## Phase 1 â€?Agent Runtime MVP

### Goal

Give the platform a **first-class Agent Run** surface without replacing the evaluation pipeline.

A user (or eval Task) can:

- register an Agent configuration as an identity (not only `Task.agent_config`)
- start a **single-shot run** (query in â†?`AgentResult` out)
- reuse the **existing** `OpenAIReActRunner` / `HttpAgentRunner` via adapter
- persist a **runtime run** record that Evaluation can later attach to

### Tech

- New package inside the existing FastAPI app (no new microservice)
- Adapter pattern: Runtime â†?`build_agent_runner()`  
- Feature flag: `RUNTIME_ENABLED=false` by default
- Lite/eager compatible (no Redis required)

### Involve (read / wrap â€?do not rewrite)

| File | Why |
| --- | --- |
| `backend/app/core/agent_runner/base.py` | `BaseAgentRunner`, `AgentResult`, `ensure_pipeline_result` |
| `backend/app/core/agent_runner/factory.py` | `build_agent_runner` |
| `backend/app/core/agent_runner/openai_runner.py` | ReAct loop (call, do not edit) |
| `backend/app/core/agent_runner/http_runner.py` | HTTP agent (call, do not edit) |
| `backend/app/api/v1/router.py` | **Additive** include only |
| `backend/app/utils/agent_config.py` | Reuse `mask_agent_config` |

### New modules (additive)

```
backend/app/core/runtime/
  __init__.py
  service.py          # create agent, start run
  models.py           # dataclasses (DB later)
  adapters/v1_runner.py
backend/app/api/v1/endpoints/runtime.py
backend/tests/unit/runtime/
```

Suggested additive APIs (do not replace `/agents/http`):

```
POST /api/v1/runtime/agents
GET  /api/v1/runtime/agents
POST /api/v1/runtime/agents/{id}/run
GET  /api/v1/runtime/runs/{id}
```

### New database

**Sprint 1 preference:** in-memory or JSON-on-existing-store behind a port, **or** one new table pair (`agents`, `agent_runs`) on `develop` only after freeze process is agreed.

**Forbidden:** ALTER `tasks`, `traces`, `metric_scores`.

### New dependencies

**None.** Do not install LangGraph in this phase.

### Risk

| Risk | Mitigation |
| --- | --- |
| Editing `openai_runner.py` â€œto make it cleanerâ€?| Forbidden |
| Breaking `/tasks/{id}/execute` | Runtime is unused by v1 pipeline in Phase 1 |
| Shadowing `/agents/http` | Namespace `/runtime/agents` |
| Creating tables on dirty `main` | Work on `develop` after owner creates it |

### Estimated effort

**1.5â€?.5 weeks** (1 senior + tests). MVP = facade + one run path + tests + lite demo.

### Phase 1 exit criteria

- [ ] v1 eval happy path still green without code changes to `celery_app/tasks.py`
- [ ] Runtime run returns the same shape as `ensure_pipeline_result`
- [ ] Secrets masked via `mask_agent_config`
- [ ] Feature flag off â†?zero behavior change

---

## Phase 2 â€?Tool Calling

### Goal

Turn the sandbox registry into a **Tool Broker** that Runtime and Evaluation both use.

Keep v1 safety: timeout, output cap, no implicit network, SSRF for HTTP.

### Tech

- Tool catalog interface over `BUILTIN_TOOLS` + plugin tools
- Per-run tool allowlist (from agent spec, not only `expected_tools`)
- Structured tool events already defined: `LogEvent.TOOL_*` â€?emit consistently from broker

### Involve (extend via new files; do not gut sandbox)

| File | Why |
| --- | --- |
| `backend/app/core/agent_runner/tool_sandbox.py` | `BUILTIN_TOOLS`, `run_tool_sandboxed`, `resolve_tools_for_suite` |
| `backend/app/api/v1/endpoints/tools.py` | List/probe â€?additive endpoints only |
| `backend/app/core/plugins/registry.py` | Plugin tools |
| `backend/app/core/agent_runner/ssrf.py` | Any future HTTP tool must call this |

### New modules

```
backend/app/core/runtime/tools/
  broker.py
  policy.py          # allowlist per agent/run
  events.py          # AOLS emit wrappers
```

Optional later tables: `tools`, `tool_grants` (not required to start).

### New dependencies

None for built-ins. **Do not** add MCP / real web search until policy exists.

### Risk

| Risk | Mitigation |
| --- | --- |
| Real network tools | Default deny; reuse SSRF |
| Changing builtin signatures | Keep `run_tool_sandboxed(name, args)` |
| Evaluation suites break if default tool set changes | Default tool set remains current builtins |

### Estimated effort

**1â€? weeks.**

### Phase 2 exit criteria

- [ ] Runtime run can restrict tools per agent
- [ ] Evaluation still uses `resolve_tools_for_suite` (or a thin wrapper)
- [ ] Probe still requires `system:config`
- [ ] No new outbound network in builtins

---

## Phase 3 â€?Evaluation Engine

### Goal

Evolve **Evaluation v2** as the product differentiator, **without replacing** `LLMJudge` / Task FSM.

Focus:

- First-class **Dataset** (import / version / reuse across Task, Experiment, Benchmark)
- Evaluation can score a **Runtime run** (not only Task-owned TestSuite)
- Close the metric loop: persist **cost + prompt/completion tokens** on *new* runtime artifacts (do not silently rewrite historical Trace rows in a migration)
- Optional extra judge dimensions â€?via scorecard JSON already supported

### Tech

- New `core/evaluation/dataset.py` (or `core/datasets/`)
- Adapter: `Trace` / Runtime run â†?judge input (already `trace.steps`)
- Benchmark service stays; Dataset feeds BenchmarkCase

### Involve (call, do not rewrite)

| File | Why |
| --- | --- |
| `backend/app/core/judge_engine/llm_judge.py` | `LLMJudge.evaluate` |
| `backend/app/core/judge_engine/scorecard.py` | `Scorecard` |
| `backend/app/core/celery_app/tasks.py` | Keep `run_full_evaluation` as v1 path |
| `backend/app/core/benchmark/service.py` | Continuous eval |
| `backend/app/core/evaluation/compare.py` | Compare |
| `backend/app/api/v1/endpoints/judges.py` | Scorecard API |
| `backend/app/api/v1/endpoints/experiments.py` | Multi-variant |
| `backend/app/api/v1/endpoints/benchmarks.py` | Regression |

### New modules

```
backend/app/core/datasets/
backend/app/api/v1/endpoints/datasets.py
backend/app/core/evaluation/runtime_bridge.py   # judge a runtime run
```

### New tables (later, additive)

`datasets`, `dataset_versions`, `dataset_cases`  
Optional: `evaluation_results` pointing to either `trace_id` or `agent_run_id`.

### New dependencies

None. Continue OpenAI-compatible Judge.

### Risk

| Risk | Mitigation |
| --- | --- |
| Duplicating Task/TestSuite | Dataset is source; Task still snapshots cases |
| Changing default 40/40/20 | Default scorecard must remain identical |
| Backfilling `traces.cost` | New writes only; no historical rewrite required |

### Estimated effort

**2â€? weeks** for Dataset + runtime-bridge + tests. Full â€œpanel judge / pairwiseâ€?is extra and can slip to v2.1.

### Phase 3 exit criteria

- [ ] Same suite can run via v1 Task pipeline **and** via Runtime + Judge bridge
- [ ] Default scorecard unchanged
- [ ] Benchmark compare still `improved | stable | regressed`

---

## Phase 4 â€?Observability

### Goal

Raise domain observability from **Intermediate â†?Intermediate+** (not full APM).

- Persist LLM/tool events that Runtime already emits
- Fill **token split + cost** on **new** runtime runs (`utils/cost.py`)
- Optional `spans` table or span JSON on `agent_runs` (not OTel export yet)
- UI: Runtime run timeline (can reuse ReactFlow Trace view)

### Tech

- Reuse AOLS `LogEvent` taxonomy (`llm.*`, `tool.*`, `agent.*`)
- New read API under `/runtime/runs/{id}/events` or `/observability/spans`
- Do not replace `/metrics` or AOLS logger

### Involve

| File | Why |
| --- | --- |
| `backend/app/core/observability/aols/` | emit / events / redaction |
| `backend/app/core/observability/tracing.py` | TraceID |
| `backend/app/core/observability/metrics.py` | Prometheus |
| `backend/app/utils/cost.py` | `calculate_cost` |
| `backend/app/models/trace.py` | Schema already has cost fields â€?**do not migrate**; write on new run model |
| `frontend/src/components/TraceFlow/TraceFlowChart.tsx` | Reuse for runtime steps |

### New modules

```
backend/app/core/runtime/observe.py
# optional later: backend/app/models/span.py
```

### New dependencies

None. **No OpenTelemetry SDK in this phase** (avoids freeze/dep risk).

### Risk

| Risk | Mitigation |
| --- | --- |
| Logging secrets in steps | Always `redact_mapping` |
| Changing Trace ORM | Write new run/span records instead |
| Perf of chatty events | Sample or batch like existing `LOG_DB_SINK` |

### Estimated effort

**1â€?.5 weeks** for persist + API + reuse DAG. Full OTel = later.

### Phase 4 exit criteria

- [ ] A Runtime run shows tokens, latency, estimated cost, errors
- [ ] v1 Trace explorer still works
- [ ] Redaction tests still pass

---

## Phase 5 â€?Security

### Goal

v2 **foundation**, not v3 Governance.

- Agent identity as a permission resource (`runtime:run`, `runtime:manage`)
- Tool allowlist persisted per agent
- Secret-at-rest **plan** (vault/env pointer instead of JSON key) â€?implement only if it does **not** change v1 `agent_config` schema
- Prompt-injection **basic** guard (length, delimiter, untrusted user block) on Runtime path only

**Do not modify** `mask_agent_config`, `redact_mapping`, `ssrf.py`, v1 RBAC matrices except **additive** permissions.

### Tech

- Additive `Permission` values (new enum members only â€?coordinate with frontend `permissions.ts`)
- Runtime policy module
- Optional `tool_grants` table

### Involve

| File | Why |
| --- | --- |
| `backend/app/core/rbac.py` | Additive permissions only |
| `frontend/src/auth/permissions.ts` | Keep in sync |
| `backend/app/core/security.py` | Keep API key auth |
| `backend/app/utils/agent_config.py` | Call only |
| `backend/app/core/observability/aols/redaction.py` | Call only |
| `backend/app/core/agent_runner/ssrf.py` | Call only |
| `backend/app/core/settings_guard.py` | Keep prod fail-fast |

### New modules

```
backend/app/core/runtime/security/
  injection_guard.py    # runtime path only
  tool_acl.py
```

### New dependencies

None.

### Risk

| Risk | Mitigation |
| --- | --- |
| Changing RBAC so old keys lose access | New perms default-granted to manager+ only |
| â€œFixingâ€?redaction | Forbidden |
| Prompt guard breaking Chinese eval suites | Off by default; eval path unchanged |

### Estimated effort

**1â€?.5 weeks** for ACL + optional guard. Vault = separate spike.

### Phase 5 exit criteria

- [ ] Viewer cannot start Runtime runs
- [ ] Agent cannot call tools outside allowlist
- [ ] v1 eval + HTTP probe + SSRF tests unchanged
- [ ] Redaction modules byte-stable vs freeze (no edits)

---

## Later (v2.x, not the first five phases)

These remain **designed, not scheduled as Sprint 1â€?**:

| Later phase | Why wait |
| --- | --- |
| LangGraph backend | Needs Runtime facade + graph schema; new dependency |
| RAG | Needs Runtime tool broker + new infra (embeddings/vector) |
| Memory | Needs session identity from Runtime |
| Production hardening | After the five phases exist on `develop` |

LangGraph placement (when approved):

```
ReactFlow editor (frontend)
    â†?agentflow.graph.v1 JSON
        â†?core/runtime/backends/langgraph
            â†?Tool broker + LLM gateway
v1 OpenAIReActRunner remains default backend
```

---

## Recommended directory (v2 additive, same monorepo)

```
backend/app/
  api/v1/endpoints/
    runtime.py              # NEW
    datasets.py             # NEW (Phase 3)
  core/
    agent_runner/           # FROZEN v1 â€?wrap only
    judge_engine/           # FROZEN core â€?extend via new files
    celery_app/             # FROZEN orchestration
    runtime/                # NEW
    datasets/               # NEW
    llm_gateway/            # NEW when multi-provider needed
frontend/src/pages/runtime/ # NEW later
docs/v2.0/                  # this folder
```

Not recommended for v2.0 start: a separate deployable `agent-runtime` service.

---

## Git strategy (do not auto-create)

Current: only `main` (dirty working tree). **No `develop`.**

Recommended when owner starts v2:

```
main                 # v1.0 release / copyright freeze
develop              # v2 integration
feature/agent-runtime
feature/tool-calling
feature/evaluation-v2
feature/observability
feature/security
# later:
feature/langgraph
feature/rag
feature/memory
```

Rules:

- Do not develop v2 on `main`
- Do not force-push `main`
- Do not upgrade pinned `backend/requirements.txt` on freeze branch

---

## Sprint 1 suggestion (after owner confirmation)

**Name:** Agent Runtime MVP (Phase 1 only)

**In:**

- `develop` + `feature/agent-runtime`
- `core/runtime` facade wrapping `build_agent_runner`
- additive `/api/v1/runtime/*`
- unit tests that mock the v1 runner
- feature flag default off

**Out:**

- LangGraph install
- Alembic on v1 tables
- edits to `openai_runner.py`, `tasks.py` (celery), `llm_judge.py`, redaction
- RAG / Memory
- dependency upgrades

**Success:** one lite demo: create runtime agent (openai or http) â†?run one query â†?see steps â†?v1 Task execute still works.

---

## Owner checklist before any coding

1. Confirm `docs/v2.0/01-v1-architecture-audit.md`
2. Snapshot the **exact** soft-copyright deposit (zip/tag) separate from the dirty tree
3. Create `develop` from the freeze commit (human)
4. Authorize Sprint 1 only
5. Reject PRs that touch frozen v1 files without an explicit exception