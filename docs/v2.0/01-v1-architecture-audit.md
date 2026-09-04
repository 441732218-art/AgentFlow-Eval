# AgentFlow Intelligence v1.x Architecture Audit

> **Document status:** Phase 0 read-only audit  
> **Audit date:** 2026-08-30  
> **Baseline:** v1.0 (soft-copyright submitted). Product version in code: `1.0.0` / `APP_VERSION = "1.0"`.  
> **Repository:** `AgentFlow-Eval`  
> **Current git HEAD:** `main` (tracks `origin/main`). **No `develop` branch exists.**  
> **Release tag (documented):** `V1.0` (`docs/releases/v1.0.0.md`)  
> **Constraint:** This document does not modify, delete, or refactor v1.0 business code.

---

## 0. Executive verdict

**v1.0 is a working Enterprise Agent Evaluation Workbench, not a full Agent Runtime / Lifecycle Platform.**

What v1.0 actually is:

- A **Task â†?TestSuite â†?Agent Runner â†?Trace â†?Judge â†?Report** pipeline.
- An observability cockpit (Dashboard / Trace DAG / Diagnosis / AOLS / Prometheus).
- An enterprise shell (API Key + RBAC + tenancy + audit + billing skeleton + plugins).

What v1.0 is **not**:

- There is **no first-class Agent entity** (no `agents` table, no `POST /agents/{id}/run`).
- There is **no executable Workflow Engine**. ReactFlow is **visualization only**.
- There is **no LangGraph**, no graph State, no conditional edges at execution time.
- There is **no RAG / Memory** (only a sandbox-simulated `retrieve_simulate` tool).
- LLM access is **OpenAI-compatible SDK only** (not a multi-provider Gateway).

v2.0 must be an **incremental evolution**: add a Runtime plane beside the existing Evaluation plane. Do not rewrite the v1 evaluation pipeline.

---

## 1. Current Technology Stack

Verified from `backend/requirements.txt`, `frontend/package.json`, `desktop/package.json`, Docker files.

| Layer | Technology | Version / evidence |
| --- | --- | --- |
| Language (backend) | Python | 3.11+ (README / CI) |
| API | FastAPI | `fastapi==0.115.0` |
| ASGI | Uvicorn / Gunicorn | `uvicorn[standard]==0.30.6`, `gunicorn==23.0.0` |
| ORM | SQLAlchemy 2.0 async | `sqlalchemy[asyncio]==2.0.35` |
| Migrations | Alembic | `alembic==1.13.2` |
| DB (lite) | SQLite + aiosqlite | `aiosqlite==0.20.0` |
| DB (prod) | PostgreSQL + asyncpg | `asyncpg==0.29.0`, `postgres:16-alpine` |
| Queue | Celery + Redis | `celery==5.4.0`, `redis==5.1.1` |
| LLM client | OpenAI official SDK | `openai==1.51.0` |
| HTTP | httpx | `httpx==0.27.2` |
| Validation | Pydantic v2 | `pydantic==2.9.2` |
| Logging | structlog | `structlog==24.4.0` |
| Metrics | Prometheus | `prometheus_client==0.21.1` |
| Rate limit | slowapi | `slowapi==0.1.9` |
| Frontend | React 18 + Vite 5 + TypeScript 5 | `frontend/package.json` `version: 1.0.0` |
| UI | Ant Design 5 | `antd ^5.21.0` |
| Graph UI | React Flow (`@xyflow/react`) | `^12.3.0` |
| State | Zustand 5 + TanStack Query 5 | listed in frontend deps |
| Charts | ECharts 6 + Recharts 3 | listed in frontend deps |
| Desktop | Electron | `desktop/package.json` `1.0.0` |
| Tests | pytest + pytest-asyncio + Vitest + Playwright | backend + frontend |

**Not present in the repository:**

- `langgraph` / LangChain runtime
- Anthropic / Google Gemini official SDKs
- Vector DB (Pinecone / Qdrant / pgvector)
- Java (`pom.xml` / `build.gradle`) â€?this is a Python + TypeScript monorepo

---

## 2. Repository Structure

Actual top-level layout (not assumed):

```
AgentFlow-Eval/
â”œâ”€â”€ backend/                 # FastAPI application
â”?  â”œâ”€â”€ app/
â”?  â”?  â”œâ”€â”€ main.py          # FastAPI entry, lifespan, health, /metrics
â”?  â”?  â”œâ”€â”€ config.py        # pydantic-settings
â”?  â”?  â”œâ”€â”€ api/v1/          # REST + WebSocket
â”?  â”?  â”œâ”€â”€ core/            # business engines
â”?  â”?  â”œâ”€â”€ models/          # SQLAlchemy ORM
â”?  â”?  â”œâ”€â”€ schemas/         # Pydantic API schemas
â”?  â”?  â”œâ”€â”€ plugins/         # example plugins
â”?  â”?  â””â”€â”€ utils/
â”?  â”œâ”€â”€ alembic/versions/    # 001 â€?016
â”?  â”œâ”€â”€ tests/               # unit + scenarios + e2e
â”?  â”œâ”€â”€ Dockerfile / docker-compose*.yml
â”?  â””â”€â”€ requirements.txt
â”œâ”€â”€ frontend/                # Vite React workbench
â”?  â”œâ”€â”€ src/pages/           # tasks, experiments, reports, benchmarks
â”?  â”œâ”€â”€ src/dashboard/       # Command Center
â”?  â”œâ”€â”€ src/traces/          # Trace explorer
â”?  â”œâ”€â”€ src/components/TraceFlow/   # ReactFlow DAG
â”?  â”œâ”€â”€ src/components/flow/        # Command Center topology
â”?  â””â”€â”€ src/auth/            # RouteGuard + permissions
â”œâ”€â”€ desktop/                 # Electron shell
â”œâ”€â”€ docs/                    # product, deploy, soft-copyright
â”œâ”€â”€ è½¯è‘—/                    # copyright submission materials
â”œâ”€â”€ scripts/                 # lite start, docker, copyright generators
â””â”€â”€ .github/workflows/       # CI / docker / desktop / release
```

**v1 domain cores (must not be rewritten in v2 Phase 1):**

| Concern | Path |
| --- | --- |
| Evaluation orchestration | `backend/app/core/celery_app/tasks.py` |
| Pipeline helpers (pure) | `backend/app/core/evaluation/pipeline.py` |
| Agent runners | `backend/app/core/agent_runner/` |
| Judge | `backend/app/core/judge_engine/` |
| Trace / AOLS | `backend/app/core/observability/` |
| Security / RBAC | `backend/app/core/security.py`, `rbac.py`, `middleware.py` |
| Config redaction | `backend/app/utils/agent_config.py` + `aols/redaction.py` |

---

## 3. Current System Architecture

v1 is a **B/S evaluation workbench** with pluggable infrastructure ports.

```
Browser / PWA / Electron
        â”? REST + WebSocket  /api/v1
        â–?FastAPI (app.main:app)
  middleware: CORS â†?RequestID â†?SecurityHeaders â†?Metrics â†?APIKeyAuth
        â”?        â”œâ”€ TaskQueuePort  (celery | eager | memory)     app/core/profiles
        â”œâ”€ CachePort      (memory | redis L2)
        â”œâ”€ EventBusPort   (in-process | redis pub/sub)
        â””â”€ MeteringPort   (noop | sqlalchemy)
                â”?                â–?     Celery / Eager: run_full_evaluation
                â”?     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”?     â–?         â–?         â–? AgentRunner  Trace     LLMJudge
 (openai/http)  ORM      (rule+LLM)
     â”? SQLite / PostgreSQL
```

**Deploy profiles** (`backend/app/core/profiles/__init__.py`):

| Profile | Queue | Cache | Bus | Typical DB |
| --- | --- | --- | --- | --- |
| `lite` | eager / memory | memory | in-process | SQLite |
| `private` | Celery | Redis L2 | Redis | PostgreSQL |
| `saas` | private + billing | Redis L2 | Redis | PostgreSQL |

This ports/adapters split is a **strength** and should be reused by v2 Runtime, not replaced.

---

## 4. Agent Execution Flow

The following path is traced from real code. There is **no standalone â€œAgent Serviceâ€?*. Execution is always **evaluation-driven**: a Task with TestSuites.

### 4.1 End-to-end path (verified)

```
User (frontend: pages/tasks/create.tsx + pages/tasks/detail.tsx)
        â†?POST /api/v1/tasks
  file: backend/app/api/v1/endpoints/tasks.py
  fn:   create_task()
  model: Task (status=CREATED, agent_config JSON)
        â†?POST /api/v1/tasks/{task_id}/execute
  file: backend/app/api/v1/endpoints/tasks.py
  fn:   execute_task()
  steps:
    - TaskStatus.CREATED â†?QUEUED (state machine)
    - billing quota gate (optional)
    - get_task_queue().enqueue("run_full_evaluation", args=(task_id,))
        â†?TaskQueuePort adapter
  files:
    backend/app/core/ports/task_queue.py          (protocol)
    backend/app/core/adapters/queue/celery_queue.py
    backend/app/core/adapters/queue/eager_queue.py
        â†?run_full_evaluation(task_id)
  file: backend/app/core/celery_app/tasks.py
  fn:   run_full_evaluation()
  steps:
    1. Load Task + TestSuites
    2. Status â†?RUNNING
    3. Celery group: run_single_test_suite per suite
    4. Status â†?JUDGING
    5. Celery group: run_judge_evaluation per trace
    6. aggregate_pipeline_results()
    7. Status â†?COMPLETED | FAILED
        â†?run_single_test_suite(test_suite_id, agent_config)
  file: backend/app/core/celery_app/tasks.py
  fn:   run_single_test_suite() â†?inner _execute()
  steps:
    - resolve_tools_for_suite(suite.expected_tools)
    - hooks.emit(HOOK_PRE_AGENT_RUN)   [masked config]
    - runner = build_agent_runner(agent_config)
    - raw = await runner.run(query, tools=..., agent_config=...)
    - ensure_pipeline_result(raw)
    - persist Trace
        â†?build_agent_runner(agent_config)
  file: backend/app/core/agent_runner/factory.py
  fn:   build_agent_runner()
  selects:
    - plugin runner (capability registry)
    - HttpAgentRunner   if runner in {http, http_agent, remote, webhook}
    - OpenAIReActRunner otherwise (default)
        â†?LLM call site
  file: backend/app/core/agent_runner/openai_runner.py
  class: OpenAIReActRunner
  fn:   _chat_completion() â†?AsyncOpenAI.chat.completions.create()
  loop: run()  Thought â†?Action â†?Observation â†?Final Answer
  tools: tool_sandbox.run_tool_sandboxed()
        â†?  OR external agent
  file: backend/app/core/agent_runner/http_runner.py
  class: HttpAgentRunner
  fn:   run() â†?HTTP POST agentflow.http.v1
  guard: ssrf.validate_http_agent_url()
        â†?Workflow execution
  â˜?DOES NOT EXIST as an executable engine.
  Visualization only:
    frontend/src/components/TraceFlow/TraceFlowChart.tsx
    frontend/src/components/flow/AgentTopologyFlow.tsx
        â†?Persist Trace
  model: backend/app/models/trace.py  class Trace
  fields written in pipeline: user_query, steps, total_tokens,
                              response_time_ms, status
  fields defined but NOT filled by run_single_test_suite:
    prompt_tokens, completion_tokens, cost,
    agent_version, prompt_version, model_version, tool_version
        â†?run_judge_evaluation(trace_id, expected_output, expected_tools)
  file: backend/app/core/celery_app/tasks.py
  fn:   run_judge_evaluation()
  judge: build_llm_judge() â†?LLMJudge.evaluate()
  file: backend/app/core/judge_engine/llm_judge.py
  persist: MetricScore rows
        â†?Evaluation aggregation
  file: backend/app/core/evaluation/pipeline.py
  fn:   aggregate_pipeline_results()
        â†?Trace / observability side-effects
  - AOLS: emit_evaluation / emit_llm / emit_agent
    backend/app/core/observability/aols/
  - Prometheus: observe_suite_run / observe_judge
    backend/app/core/observability/metrics.py
  - Request TraceID: backend/app/core/observability/tracing.py
  - WS live status: backend/app/core/events.py â†?ws_hub
        â†?GET /api/v1/traces , GET /api/v1/reports , Dashboard / Diagnosis
  final UI response
```

### 4.2 Unified runner contract (already a v2 Runtime seed)

`backend/app/core/agent_runner/base.py`

- Class: `BaseAgentRunner`
- Method: `async run(query, tools=None, *, agent_config=None)`
- Result: `AgentResult` or dict â†?`ensure_pipeline_result()`

This contract is the correct **compatibility layer** for v2. Do not break it.

### 4.3 What â€œAgentâ€?means in v1

| Concept | v1 reality |
| --- | --- |
| Agent identity | JSON blob `Task.agent_config` (runner/model/url/scorecard) |
| Agent loop | `OpenAIReActRunner.run()` max_iterations (default 5) |
| Agent as HTTP service | `HttpAgentRunner` + `POST /api/v1/agents/http/probe` |
| Plugin agent | `app.plugins.examples.echo_runner` |

There is **no** `agents` resource, version table, or session store.

---

## 5. Workflow Architecture

### 5.1 Answers (required)

| # | Question | Answer |
| --- | --- | --- |
| 1 | Implementation | **No backend Workflow Engine.** Execution is a linear Celery pipeline + ReAct loop. |
| 2 | ReactFlow? | **Yes, frontend only** (`@xyflow/react` ^12.3.0). |
| 3 | How stored? | ReAct `steps` JSON on `traces.steps`. Topology for Command Center is **computed at read time** by dashboard API, not persisted as a graph. |
| 4 | Workflow JSON / Schema | **None** for executable graphs. Trace step dicts are informal (`thought/action/observation/final_answer`). HTTP protocol: `docs/http-agent-protocol.md`. |
| 5 | How executed? | Not executed. ReactFlow **renders** persisted steps. |
| 6 | Node types | UI nodes: `thought`, `action`, `observation`, `final_answer` (`TraceFlowChart.tsx` `STEP_STYLES`). Dashboard topology kinds: pipeline stages from `dashboard.py`. |
| 7 | Edges | Sequential UI edges only (`source â†?target` in ReactFlow). No runtime edge evaluator. |
| 8 | State? | **No graph State object.** Loop state is local variables in `OpenAIReActRunner.run()`. Task has a **status state machine** only. |
| 9 | Conditional branch? | **No.** ReAct tool-choice is the only â€œbranchâ€? |
| 10 | Agent Runtime prototype? | **Yes, a prototype:** `BaseAgentRunner` + ReAct loop + tool sandbox + HTTP runner + plugin runners. Not a lifecycle runtime. |

### 5.2 Real files / classes / functions

| Role | Path | Symbol |
| --- | --- | --- |
| Trace DAG UI | `frontend/src/components/TraceFlow/TraceFlowChart.tsx` | `TraceFlowChart` |
| Command Center topology | `frontend/src/components/flow/AgentTopologyFlow.tsx` | `AgentTopologyFlow` |
| Topology payload | `backend/app/api/v1/endpoints/dashboard.py` | horizontal ReAct pipeline for ReactFlow |
| ReAct loop | `backend/app/core/agent_runner/openai_runner.py` | `OpenAIReActRunner.run` |
| Step dataclass | same file | `ReActStep` |
| HTTP â€œworkflowâ€?| `backend/app/core/agent_runner/http_runner.py` | `HttpAgentRunner.run` |
| Task status FSM | `backend/app/models/task.py` | `TaskStatus.allowed_transitions` |

### 5.3 Relationship to LangGraph

Current â€œworkflowâ€?is **post-hoc visualization of a ReAct trace**, not a graph runtime.

LangGraph should be introduced later as a **new execution backend** behind `BaseAgentRunner`, not as a replacement of Celery evaluation orchestration.

---

## 6. LLM Integration

### 6.1 What is actually supported

There is **one production client**: `openai.AsyncOpenAI`.

```
Provider (string label only)
    â†?factory.build_agent_runner()
    reads agent_config.provider | default "openai"
    reads agent_config.base_url | settings.OPENAI_BASE_URL
    reads agent_config.api_key  | settings.OPENAI_API_KEY
    â†?OpenAIReActRunner / LLMJudge
    â†?AsyncOpenAI(api_key, base_url).chat.completions.create(...)
    â†?Call sites:
  OpenAIReActRunner._chat_completion()
  LLMJudge (refine path in llm_judge.py)
  multimodal vision (VISION_MODEL, OpenAI-compatible)
```

| Provider | Native adapter? | How it could work today |
| --- | --- | --- |
| OpenAI | **Yes** | Default. Models: `gpt-4o-mini` default, pricing table in `utils/cost.py` |
| DeepSeek | **No SDK** | Possible only if OpenAI-compatible `base_url` is set |
| Claude / Anthropic | **No** | Frontend `model-provider.ts` lists `anthropic` as **deprecated unused types** |
| Gemini | **No** | Not in backend |
| Azure / Zhipu / local | **No backend** | Deprecated frontend types only |

`provider` on `OpenAIReActRunner` is used for **AOLS log labels**, not for routing to different SDKs.

### 6.2 LLM Gateway recommendation

**Yes â€?add a new LLM Gateway / Provider Adapter layer in v2**, as a **new module**, without changing `OpenAIReActRunner` internals in Phase 1.

Suggested evolution:

```
v1: OpenAIReActRunner â†?AsyncOpenAI
v2: Runtime / Judge â†?LlmGateway.port â†?adapters (openai | openai-compatible | later anthropic/gemini)
```

Do **not** rip out `AsyncOpenAI` from v1 runners. Wrap it.

---

## 7. Evaluation Architecture

### 7.1 How it is implemented

Hybrid engine:

1. **Rule path** always runs (`calc_tool_accuracy`, lexical/CJK answer scoring).
2. **LLM-as-Judge refine** when `OPENAI_API_KEY` is present.
3. Fallback to rules on timeout / error / missing key.

Core types:

| Piece | Path | Symbol |
| --- | --- | --- |
| Judge ABC | `backend/app/core/judge_engine/base.py` | `BaseJudge`, `JudgeResult` |
| Hybrid judge | `backend/app/core/judge_engine/llm_judge.py` | `LLMJudge.evaluate` |
| Scorecard | `backend/app/core/judge_engine/scorecard.py` | `Scorecard`, `default_scorecard` |
| Rule metrics | `backend/app/core/judge_engine/metrics.py` | `calc_tool_accuracy`, `extract_answer_text` |
| Orchestration | `backend/app/core/celery_app/tasks.py` | `run_judge_evaluation`, `run_full_evaluation` |
| Aggregation | `backend/app/core/evaluation/pipeline.py` | `aggregate_pipeline_results` |
| Compare | `backend/app/core/evaluation/compare.py` | experiment/benchmark compare helpers |
| Benchmark | `backend/app/core/benchmark/service.py` | run + regression compare |

### 7.2 Data model

| Table / model | Role |
| --- | --- |
| `tasks` / `Task` | Evaluation job aggregate + `agent_config` |
| `test_suites` / `TestSuite` | Dataset row: `user_query`, `expected_output`, `expected_tools` |
| `traces` / `Trace` | One suite execution |
| `metric_scores` / `MetricScore` | Per-dimension score + human review override |
| `experiments` / `ExperimentRun` | Multi-variant compare (suite snapshot JSON) |
| `benchmarks` / `BenchmarkCase` / `BenchmarkRun` / `BenchmarkResult` | Continuous evaluation |
| `ab_*` | Product A/B (assignment/events), not LLM eval |

**No standalone `datasets` / `evaluation_tasks` / `evaluation_results` tables.** Task + TestSuite play those roles.

### 7.3 Evaluation APIs (existing â€?do not change)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/tasks` | Create eval task |
| POST | `/api/v1/tasks/{id}/execute` | Start pipeline |
| GET | `/api/v1/tasks` `/tasks/{id}` | List / detail |
| GET | `/api/v1/traces` | Trace list |
| POST | `/api/v1/traces/{id}/human-review` | Human override |
| GET | `/api/v1/judges/scorecards/default` | Default 40/40/20 card |
| POST | `/api/v1/judges/scorecards/validate` | Validate custom card |
| CRUD + run | `/api/v1/experiments` `/compare` | Multi-variant |
| CRUD + run | `/api/v1/benchmarks` `/{id}/run` `/compare` | Continuous eval |
| GET | `/api/v1/reports` | Report aggregation |

### 7.4 Execution flow

See Â§4. After traces exist: `LLMJudge.evaluate(trace_steps, expected_output, expected_tools)` â†?`MetricScore` rows â†?`aggregate_pipeline_results`.

### 7.5 Current metrics

Default scorecard (`default_scorecard()`):

| Dimension | Weight | Method |
| --- | --- | --- |
| `tool_accuracy` | 40 | `rule_tool` |
| `answer_correctness` | 40 | `llm_or_lexical` |
| `reasoning_coherence` | 20 | `llm_only` |

Also: human review (`is_human_reviewed`, `human_score`, `reviewer`), `confidence` column exists.

### 7.6 LLM-as-a-Judge?

**Yes.** `LLMJudge` + optional plugin judges (`length` example). Cached LRU. Soft timeout. Resilience policy.

### 7.7 Dataset?

**Partial.** TestSuite / BenchmarkCase / Experiment `suite_snapshot` are datasets-in-practice. Missing: first-class Dataset versioning, sharing, labels, split train/eval, import marketplace.

### 7.8 Benchmark?

**Yes (v1 continuous eval).** `Benchmark` + `BenchmarkRun` + compare `improved | stable | regressed` (`docs/benchmarks.md`, `core/benchmark/service.py`).

### 7.9 Gap vs v2 Evaluation Engine

Already strong for a v1 product. Gaps to â€œenterprise Evaluation Engine v2â€?

| Missing | Notes |
| --- | --- |
| First-class Dataset + version | Today glued to Task/Benchmark |
| Judge panel / multi-judge consensus | Single judge path |
| Inter-rater reliability | Human review exists, no stats |
| Pairwise / preference eval | Only absolute scores |
| Trajectory-level / process metrics | Mostly outcome + tool set match |
| Cost/latency as first-class eval metrics | Fields exist; pipeline does not persist cost |
| Online eval / production traces as dataset | Offline suites only |
| Evaluation versioning independent of Task FSM | Coupled to Task status |

**Distance:** Evaluation is the **most mature** v1 subsystem (~60â€?0% of a v2 engine). v2 should **extend**, not replace.

---

## 8. Trace / Observability

### 8.1 How Trace is implemented

Two different â€œtracesâ€?

1. **Domain Trace (evaluation artifact)** â€?ORM `Trace`, JSON `steps`, API `/api/v1/traces`.
2. **Correlation TraceID** â€?`contextvars` in `observability/tracing.py`, headers `X-Request-ID` / `X-Trace-ID`, passed into Celery as `_trace_id`.

Plus **AOLS** structured events and **Prometheus** `/metrics`.

### 8.2 Data structure

`Trace` (`backend/app/models/trace.py`):

- `test_suite_id`, `user_query`
- `steps` JSON (ReAct step array)
- `total_tokens`, `response_time_ms`, `status`
- `prompt_tokens`, `completion_tokens`, `cost` (columns exist)
- `agent_version`, `prompt_version`, `model_version`, `tool_version` (columns exist)

`AgentLog` (`agent_logs` table) stores structured AOLS events.

### 8.3 Capability checklist

| Capability | Exists? | Where |
| --- | --- | --- |
| Span model | **No** | No `spans` table / OpenTelemetry spans |
| LLM call recorded | **Yes** (logs) | `emit_llm` `llm.started/completed/failed` in `_chat_completion` and judge |
| Tool call recorded | **Yes** (logs + step JSON) | `LogEvent.TOOL_*`; step `action` / `observation` |
| Token recorded | **Partial** | `total_tokens` persisted; prompt/completion split **not written** by pipeline |
| Latency recorded | **Yes** | `response_time_ms` on Trace; `latency_ms` in AOLS |
| Cost recorded | **Schema yes, pipeline no** | `utils/cost.py` `calculate_cost`; `run_single_test_suite` does not set `Trace.cost` |
| Error recorded | **Yes** | Trace `status=failed`, `error_message` in suite result, AOLS `LLM_FAILED` / `EVALUATION_FAILED`, `X-Error-ID` |

Diagnosis heuristics: `backend/app/core/diagnosis/engine.py` (`agent_loop`, `tool_failure`, `token_drift`, `prompt_drift`, `timeout`).

### 8.4 Maturity judgment

**Current level: Intermediate.**

Reasons:

- Stronger than â€œbasic logsâ€? domain Trace + DAG UI + correlation IDs + Prometheus + structured event taxonomy + diagnosis.
- Weaker than â€œadvancedâ€? no span tree, no OTel export, cost/token split not persisted, no user-facing LLM/tool span explorer, no sampling/retention productization.

---

## 9. Security

### 9.1 API Key / Secret

| Mechanism | Path | Symbol |
| --- | --- | --- |
| Optional API key auth | `backend/app/core/security.py` | `authenticate_api_key`, `extract_api_key`, `ApiKeyEntry` |
| Middleware gate | `backend/app/core/middleware.py` | `APIKeyAuthMiddleware` |
| Config | `backend/app/config.py` | `AUTH_ENABLED`, `API_KEYS` (`secret:actor:role`) |
| Prod fail-fast | `backend/app/core/settings_guard.py` | `enforce_production_settings` |

Secrets in `agent_config` (per-task `api_key`, HTTP `Authorization` headers) are stored in JSON on `tasks.agent_config`. **They are masked on output/logs, but still sit in the database in plaintext.** This is a recorded risk, not a v1 rewrite item.

### 9.2 Redaction (do not modify)

| Entry | Path | Symbol |
| --- | --- | --- |
| Public mask API | `backend/app/utils/agent_config.py` | `mask_agent_config` |
| Implementation | `backend/app/core/observability/aols/redaction.py` | `redact_mapping`, `redact_value` |

Used by: evaluation hooks (`HOOK_PRE_AGENT_RUN` logs), task response serialization, cache, structured logs.

**Freeze these modules for copyright + security consistency.** v2 may *call* them, not rewrite them.

### 9.3 Prompt Injection

**Not handled.** Grep of backend `app/` finds no prompt-injection / jailbreak guard. User `TestSuite.user_query` is sent raw into the ReAct system prompt and HTTP agent.

### 9.4 Tool permission

**Sandbox allowlist, not ACL.**

- Registry: `BUILTIN_TOOLS` in `tool_sandbox.py`
- Execute: `run_tool_sandboxed` (timeout 3s, output truncate 4000, no network)
- Built-ins: `calculator`, `web_search` (simulated), `current_datetime`, `json_get`, `regex_extract`, `time_query`, `retrieve_simulate`
- Plugin tools via capability registry
- Probe API: `POST /api/v1/tools/probe` requires `system:config`

No per-user / per-agent tool grants. No MCP permission model.

### 9.5 User permission

**Yes â€?RBAC.**

- `backend/app/core/rbac.py`: `Role`, `Permission`, `require_permission`
- Roles: `system_admin`, `tenant_admin`, `manager`, `reviewer`, `member`, `viewer` (+ legacy aliases)
- Frontend: `frontend/src/auth/permissions.ts`, `RouteGuard`
- Permissions include `task:*`, `evaluation:*`, `benchmark:*`, `billing:*`, `tenant:*`

Auth is **API-key-as-user**, not OIDC/SSO/password users.

### 9.6 Agent permission

**No.** Agents are config JSON, not principals. No agent-to-tool / agent-to-data policy.

### 9.7 SSRF

**Yes, for HTTP Agent.**

- `backend/app/core/agent_runner/ssrf.py`: `validate_http_agent_url`, `SsrfBlockedError`
- Blocks private/loopback/link-local/metadata, optional DNS resolve (`HTTP_AGENT_SSRF_RESOLVE_DNS`)
- Used by `HttpAgentRunner` and `POST /api/v1/agents/http/probe`

### 9.8 Data leak risks (record only)

1. `agent_config` secrets persisted plaintext.
2. AUTH defaults **off** (`AUTH_ENABLED=False`) â€?fine for lite demo, dangerous if prod misconfigured (mitigated by `settings_guard` when `ENV=prod`).
3. Trace `steps` may contain user data / tool I/O; redaction is for keys, not PII in content.
4. Plugin directory scan unless `PLUGIN_STRICT_MODE`.
5. No prompt-injection isolation between suite text and system prompt.

### 9.9 Distance to enterprise Agent Governance

**Far.** v1 has a solid **platform security shell** (authz, SSRF, sandbox, audit, redaction). It does **not** have Agent Governance: policy engine, agent identity, tool entitlements, data classification, prompt firewall, approval workflows, runtime kill-switch as a product.

Treat Governance as **v3.0** (per product strategy). v2 only adds foundations (agent identity + tool ACL + keep v1 redaction/SSRF).

---

## 10. Database

### 10.1 Existing tables (Alembic 001â€?16 + models)

| Table | Model | Origin |
| --- | --- | --- |
| `tasks` | `Task` | 001 + 003 archive + 005 created_by + tenant |
| `test_suites` | `TestSuite` | 001 |
| `traces` | `Trace` | 001 + 002 token/cost/version cols |
| `metric_scores` | `MetricScore` | 001 + human review cols |
| `audit_logs` | `AuditLog` | 004 + 016 tenant |
| `experiments`, `experiment_runs` | `Experiment`, `ExperimentRun` | 006 |
| `media_assets` | `MediaAsset` | 008 |
| `ab_experiments`, `ab_variants`, `ab_assignments`, `ab_events` | AB models | 009 |
| billing: `billing_plans`, `subscriptions`, `usage_records`, `quota_balances`, `invoices` | billing | 010 + 014 |
| `slow_task_events` | `SlowTaskEvent` | 011 |
| `agent_logs` | `AgentLog` | 012 |
| `tenants`, `tenant_members` | `Tenant`, `TenantMember` | 013 |
| `benchmarks`, `benchmark_cases`, `benchmark_runs`, `benchmark_results` | benchmark | 015 |

SQLite also gets additive `ALTER` in `main.py` `_ensure_sqlite_columns` (do not change).

### 10.2 Tables that do **not** exist (v2 candidates only â€?no migration now)

| Suggested | Purpose | v2 phase |
| --- | --- | --- |
| `agents` | First-class agent identity / config pointer | Runtime MVP |
| `agent_versions` | Reproducible agent snapshots | Runtime |
| `agent_sessions` / `agent_runs` | Interactive / runtime executions â‰?eval Task | Runtime |
| `tools` | Registered tools (beyond in-memory `BUILTIN_TOOLS`) | Tool Calling |
| `tool_grants` | Agent/user â†?tool ACL | Security |
| `workflows`, `workflow_versions` | Graph definition JSON | LangGraph later |
| `workflow_runs` | Graph execution instances | LangGraph later |
| `models` / `model_providers` | LLM catalog | LLM Gateway |
| `knowledge_bases`, `documents`, `chunks` | RAG | after Runtime |
| `memories` | Long-term memory | after RAG |
| `datasets`, `dataset_versions` | Eval v2 | Evaluation Engine |
| `spans` | OTel-style spans | Observability |
| `policies` | Governance | v3 |

**Do not create these in Phase 0. Do not run Alembic.**

---

## 11. API

Registered in `backend/app/api/v1/router.py` (prefix `/api/v1`):

| Prefix | Module | Domain |
| --- | --- | --- |
| `/me` | `me.py` | Current actor / role / permissions |
| `/tenants` | `tenants.py` | Multi-tenant orgs |
| `/billing` | `billing.py` | Plans / quota / Stripe mock |
| `/benchmarks` | `benchmarks.py` | Continuous eval |
| `/observability` | `observability.py` | KPI / timeseries |
| `/tasks` | `tasks.py` | Eval tasks + execute |
| `/dashboard` | `dashboard.py` | Command Center |
| `/diagnosis` | `diagnosis.py` | Heuristic RCA |
| `/logs` | `logs.py` | AOLS query |
| `/media` | `media.py` | Multimodal assets |
| `/ab` | `ab.py` | Product A/B |
| `/experiments` | `experiments.py` | Config compare |
| `/traces` | `traces.py` | Trace CRUD-ish + human review |
| `/reports` | `reports.py` | Score reports |
| `/audit` | `audit.py` | Audit log |
| `/tools` | `tools.py` | List + probe sandbox tools |
| `/agents/http` | `agents_http.py` | Contract + probe (not Agent CRUD) |
| `/judges` | `judges.py` | Scorecard |
| `/plugins` | `plugins.py` | Plugin market |
| `/settings` | `settings.py` | Public / admin settings |
| WS | `ws.py` | Live task status |
| `/health`, `/health/live`, `/health/ready`, `/metrics` | `main.py` | Ops |

**v2 API rule:** keep every v1 path and payload stable. New runtime APIs should be **additive** (`/api/v1/runtime/...` or later `/api/v2/...`) and must not redefine `POST /tasks/{id}/execute`.

Example **additive** (design only):

```
POST /api/v1/runtime/agents
GET  /api/v1/runtime/agents
POST /api/v1/runtime/agents/{id}/run
GET  /api/v1/runtime/runs/{id}
GET  /api/v1/runtime/runs/{id}/events
```

Do **not** invent a parallel `POST /agents` that shadows `/agents/http`.

---

## 12. Testing

### Backend

~60 unit modules under `backend/tests/unit/` covering: pipeline, runners, SSRF, judge, scorecard, RBAC, tenancy, billing, plugins, cache, AOLS, HTTP probe, benchmarks, experiments, API contract.

Also:

- `backend/tests/scenarios/test_eval_happy_path_lite.py`
- `backend/tests/test_e2e.py`
- `backend/app/core/celery_app/tests/test_tasks.py`

### Frontend

Thin: `format.test.ts`, `performance.test.ts`. Playwright script exists (`test:e2e`).

### Gap

Runtime / LangGraph / RAG will need a **new test package** (`backend/tests/unit/runtime/`) so v1 suites stay green and frozen.

---

## 13. Deployment

| Mode | How | Evidence |
| --- | --- | --- |
| Lite | `scripts/start-lite.ps1`, `docker-compose.lite.yml` | SQLite + eager, no Redis |
| Private Docker | `backend/docker-compose.yml` | Postgres 16, Redis 7, migrate, backend, celery, frontend |
| SaaS profile | `DEPLOY_PROFILE=saas` + billing flags | settings + adapters |
| Desktop | Electron `desktop/` | Win/mac/linux builders |
| CI | `.github/workflows/` | test, docker, desktop, release `v1.*` |
| Health | `/health/live` `/health/ready` | `main.py` |

v2 Runtime must run in **lite (eager)** first so copyright-era demo path keeps working.

---

## 14. Technical Debt

Recorded only â€?**do not fix in this phase.**

### P0 (must address before / while adding Runtime â€?by isolation, not rewrite)

| ID | Debt | Evidence |
| --- | --- | --- |
| P0-1 | No first-class Agent; everything hangs on Task | `models/task.py` `agent_config` JSON |
| P0-2 | Working tree on `main` is heavily dirty (v1 files modified + many untracked copyright scripts) | `git status` |
| P0-3 | No `develop` branch; v2 work would land on `main` | `git branch -a` |
| P0-4 | Trace cost / token split columns unused by pipeline | `tasks.py` `Trace(...)` constructor vs model fields |

### P1 (should optimize later)

| ID | Debt |
| --- | --- |
| P1-1 | Single LLM SDK; `provider` is a log label |
| P1-2 | Secrets in `agent_config` JSON at rest |
| P1-3 | Frontend tests almost absent |
| P1-4 | `tool_sandbox.py` contains garbled comments (encoding) â€?do not â€œclean upâ€?during copyright freeze |
| P1-5 | Judge/score persist does not write `Trace.cost` |
| P1-6 | AUTH off by default (correct for lite; ops risk) |

### P2 (future)

| ID | Debt |
| --- | --- |
| P2-1 | No prompt injection defense |
| P2-2 | No OTel spans |
| P2-3 | Plugin market is in-memory catalog |
| P2-4 | Billing/Stripe is mock-first |
| P2-5 | Simulated RAG tool â‰?RAG system |

---

## 15. Current Architecture Strengths

1. **Clear evaluation domain model** â€?Task / TestSuite / Trace / MetricScore is coherent and copyright-worthy.
2. **Unified runner contract** â€?`BaseAgentRunner.run()` already isolates OpenAI / HTTP / plugins.
3. **Production-minded ops** â€?health probes, settings guard, rate limit, security headers, audit, AOLS redaction.
4. **Ports & adapters** â€?queue/cache/bus/metering profiles enable lite vs private without rewriting business logic.
5. **Judge + Scorecard + Experiment + Benchmark** â€?real product differentiation vs a chat UI.
6. **SSRF + tool sandbox** â€?safer than typical â€œagent demoâ€?code.
7. **ReactFlow already in the UI stack** â€?can become a workflow editor later without a new graph library.
8. **Plugin hooks** around agent run and judge â€?extension point for v2 without editing pipeline.

---

## 16. Current Architecture Weaknesses

1. Product name says â€œIntelligence / Agent platformâ€? **code is an eval workbench**.
2. **No Agent Runtime** as a product surface (no session, no graph, no streaming agent API).
3. **Workflow is a screenshot feature**, not an engine.
4. **LLM coupling** to OpenAI SDK.
5. **Observability is Intermediate** â€?events exist, spans do not; cost not closed-loop.
6. **Identity is API keys**, not users/SSO.
7. **main is not clean** â€?risky for a submitted copyright baseline.
8. Soft-copyright tree (`docs/soft-copyright/`, `è½¯è‘—/`, generators) is large and mixed with product code.

---

## 17. v2.0 Migration Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Editing v1 Task/Judge/Trace modules | Soft-copyright baseline drift; regression | New packages only; wrap via `BaseAgentRunner` |
| Introducing LangGraph into `celery_app/tasks.py` | Couples eval SLA to graph runtime | LangGraph is a runner backend, not the orchestrator |
| Changing `/api/v1/tasks` semantics | Breaks frontend + copyright API descriptions | Additive `/runtime` APIs |
| New Alembic on v1 tables | Schema drift vs submitted design | New tables only, later, on develop |
| Dependency upgrades (`openai`, FastAPI, React) | Reproducibility / legal baseline | Freeze v1 lockfiles |
| â€œCleanupâ€?of garbled comments / refactors | Diff noise vs deposited source | Forbidden in Phase 0â€? |
| Implementing RAG before Runtime | Distracts from Agent Quality Platform | Defer |
| Running v2 work on `main` | Mixes freeze and evolution | Recommend `develop` + feature branches (do not auto-create) |

---

## 18. v1.x â†?v2.0 Migration Strategy

**Incremental Evolution, not Rewrite.**

```
v1.0 frozen baseline (soft copyright)
        â†?compatibility layer
  - keep BaseAgentRunner
  - keep run_full_evaluation
  - keep mask_agent_config / redact_mapping / SSRF
        â†?v2 Agent Runtime (new package)
  - Agent identity + session/run
  - optional graph backend later
        â†?v1 Evaluation pipeline calls Runtime OR still calls runners directly
        â†?gradual migration of HTTP/OpenAI runners behind Runtime facade
```

**Compatibility rules:**

1. v1 `POST /tasks/{id}/execute` must keep working forever in v2.
2. v2 Runtime may *internally* call `build_agent_runner()`.
3. New DB tables are additive.
4. ReactFlow stays the visualizer; editor comes later and **exports** JSON, does not replace Trace DAG.
5. LangGraph (if introduced) lives under Runtime, feature-flagged, lite-safe.

---

## 19. Recommended Architecture

Do **not** explode the monorepo into a separate `agent-runtime/` top-level service in Sprint 1. The current repo is already a modular monolith with ports. Split services only if scale requires it later.

```
Frontend (existing workbench + new Runtime pages)
        â†?API Gateway = existing FastAPI app (v1 routes frozen)
        â†?â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”?â”? Agent Platform (existing)                  â”?â”? tasks / experiments / benchmarks / rbac    â”?â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”?                â”?calls (later)
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”?â”? Agent Runtime (NEW, v2)                    â”?â”? session / state / loop / tool broker       â”?â”? adapters â†?existing OpenAIReActRunner      â”?â”? future â†?LangGraph backend                 â”?â””â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”?        â–?          â–?          â–?   LLM Gateway   Tools      Memory/RAG (later)
   (NEW wrap)    (extend sandbox)
        â–?   Evaluation (EXISTING, evolve in place via new datasets API)
        â–?   Observability (EXISTING AOLS + future spans)
        â–?   Security (EXISTING shell + future grants)
```

### Recommended new directories (additive)

```
backend/app/core/runtime/          # Agent Runtime MVP
  agent/
  session/
  state/
  loop/
  adapters/                       # wrap v1 runners
backend/app/core/llm_gateway/      # later, not Sprint 1 required
backend/app/api/v1/endpoints/runtime.py   # additive routes

frontend/src/pages/runtime/        # later UI
```

**Do not** create a parallel `evaluation-engine/` that copies `judge_engine`. Evaluation v2 extends `judge_engine` + new dataset module.

---

## 20. Recommended Next Steps

1. **Protect the v1.0 freeze** (process, not code): archive the exact submitted source tree; do not keep developing on dirty `main`.
2. **Create `develop` from the freeze point** when you decide to start v2 (human action â€?this audit does not create branches).
3. Confirm this audit, then enter **Sprint 1 â€?Agent Runtime MVP** only:
   - new `core/runtime` package
   - wrap `build_agent_runner`
   - additive run API
   - no LangGraph install
   - no v1 pipeline edits
4. Keep Evaluation as the **product differentiator**; Runtime exists so Evaluation can score *real* agents, not only ReAct-in-process.

**Stop here. Do not start Sprint 1 until the project owner confirms.**

---

## Appendix A. Module reassessment (P0 / P1 / P2)

### P0 â€?Agent Runtime

| Item | Assessment |
| --- | --- |
| Current | Prototype ReAct + HTTP + plugins |
| Missing | Agent entity, session, streaming, graph state, planner |
| Difficulty | Medium (can wrap existing runner) |
| Relation | Calls `agent_runner`, must not replace celery eval |
| New service? | No (same FastAPI) |
| New tables? | Yes later: `agents`, `agent_runs` |
| New API? | Yes, additive |
| New deps? | None for MVP |
| Risk | Accidental rewrite of `openai_runner.py` |
| Order | **First** |

### P0 â€?Tool Calling

| Item | Assessment |
| --- | --- |
| Current | Sandbox builtins + OpenAI function calling + plugin tools |
| Missing | Persistence, ACL, real connectors, MCP, human-in-the-loop |
| Difficulty | Medium |
| Relation | Extends `tool_sandbox.py` via registry; do not gut sandbox |
| New service? | No |
| New tables? | `tools`, `tool_grants` later |
| New API? | Extend `/tools` additively |
| New deps? | None at first |
| Risk | Enabling real network tools without SSRF/ACL |
| Order | **Second** |

### P0 â€?LangGraph Runtime

| Item | Assessment |
| --- | --- |
| Current | Not present; ReactFlow is visual |
| Missing | Graph compile/execute, state, conditional edges |
| Difficulty | High if done as rewrite; medium as optional backend |
| Relation | Behind Runtime; ReactFlow becomes editor later |
| New service? | No |
| New tables? | `workflows`, `workflow_versions`, `workflow_runs` |
| New API? | Additive execute |
| New deps? | `langgraph` **later only**, not now |
| Risk | Replacing Celery pipeline; license/version freeze |
| Order | **After Runtime MVP + Tool Calling** (not Sprint 1) |

### P1 â€?RAG

| Item | Assessment |
| --- | --- |
| Current | `retrieve_simulate` mock + multimodal extractors |
| Missing | KB, chunking, embeddings, vector index |
| Difficulty | High |
| Relation | New; can be a tool used by Runtime |
| Order | After Runtime |

### P1 â€?Memory

| Item | Assessment |
| --- | --- |
| Current | None (messages list inside one `run()`) |
| Missing | Short/long-term, per-agent, per-tenant memory |
| Order | After RAG or parallel light session memory |

### P1 â€?Evaluation v2

| Item | Assessment |
| --- | --- |
| Current | Strong v1 engine |
| Missing | Dataset product, multi-judge, process metrics |
| Difficulty | Medium |
| Relation | **Extend** `judge_engine` / benchmarks |
| Order | After Runtime can produce richer traces |

### P2 â€?Observability

| Item | Assessment |
| --- | --- |
| Current | Intermediate AOLS + Prometheus + Trace JSON |
| Missing | Spans, persist cost, OTel |
| Order | After Runtime emits richer events |

### P2 â€?Security / Governance

| Item | Assessment |
| --- | --- |
| Current | Platform shell strong; Agent governance weak |
| Missing | Prompt firewall, agent ACL, secret vault |
| Order | Foundations in v2; full governance is v3 |

---

## Appendix B. LangGraph planning (design only)

| # | Question | Recommendation |
| --- | --- | --- |
| 1 | Introduce LangGraph? | **Yes, later.** Not Sprint 1. After Runtime facade exists. |
| 2 | Which layer? | `core/runtime/backends/langgraph/` behind `BaseAgentRunner`. |
| 3 | ReactFlow â†?LangGraph | ReactFlow = editor/visualizer. LangGraph = executor. Shared JSON graph schema. |
| 4 | Workflow JSON â†?Graph | New schema `agentflow.graph.v1` (nodes, edges, condition). Compiler in Runtime. v1 Trace JSON stays as **logs**, not source of graph. |
| 5 | State | Typed dict: `messages`, `iteration`, `tool_results`, `tenant_id`, `run_id`. Persist on `workflow_runs`. |
| 6 | Node executor | Interface `execute(node, state) -> state`. Node kinds: llm, tool, judge, http_agent, condition. |
| 7 | Tool node | Call existing `run_tool_sandboxed` / tool broker. |
| 8 | Conditional edge | Predicate functions on State; ReactFlow edge `condition` field. |
| 9 | Keep existing engine? | **Yes.** Celery eval pipeline remains the evaluation orchestrator. |
| 10 | Avoid big-bang | Feature flag `RUNTIME_BACKEND=react|langgraph`. Default `react` = current `OpenAIReActRunner`. |

---

## Appendix C. Git strategy (recommendation only â€?not executed)

Current:

```
* main  â†?origin/main
  (no develop)
```

Recommended later (human creates):

```
main          # frozen v1.0 / release
  â””â”€ develop  # v2 integration
       â”œâ”€ feature/agent-runtime
       â”œâ”€ feature/tool-calling
       â”œâ”€ feature/langgraph
       â”œâ”€ feature/rag
       â”œâ”€ feature/memory
       â”œâ”€ feature/evaluation-v2
       â”œâ”€ feature/observability
       â””â”€ feature/security
```

**This audit did not create branches.**

---

## Appendix D. Soft-copyright protection checklist

- [x] No business code modified in this phase
- [x] No dependency upgrade
- [x] No Alembic / API / DB change
- [ ] Owner should snapshot the **exact** submitted file set (tag / zip) separately from the dirty working tree
- [ ] Do not â€œformatâ€?or â€œfix encodingâ€?in `tool_sandbox.py` or other deposited files
- [ ] v2 docs live under `docs/v2.0/` only (new copyright generation later, not now)