# Runtime Boundary Decision

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 6.8 — Runtime Boundary Decision Audit  
**Date:** 2026-08-31  
**Type:** Read-only architecture decision audit  
**Prerequisite:** Phase 6.5 Audit (`docs/v2.0/runtime-phase6.5-audit.md`)

---

## Runtime Boundary Decision

This document freezes architectural boundaries before Phase 7 Runtime API development. It answers: which Runtime stack is authoritative, how the legacy stack is retired, and where Memory / Execution / Tool / Trace boundaries lie.

---

## 1. Current Architecture

### 1.1 Phase 1–6 Runtime (`backend/app/runtime/`)

**Verified structure (2026-08-31):**

```
backend/app/runtime/
├── __init__.py
├── context.py
├── executor/
│   ├── __init__.py
│   └── executor.py          # AgentExecutor, ExecutionResult
├── pipeline/
│   ├── __init__.py
│   ├── hooks.py             # ExecutionHook
│   └── pipeline.py          # ExecutionPipeline
├── tools/
│   ├── __init__.py
│   └── registry.py          # Tool, ToolRegistry
├── memory/
│   ├── __init__.py
│   ├── provider.py          # MemoryProvider (ABC)
│   ├── memory.py            # InMemoryProvider
│   └── hook.py              # MemoryHook
├── knowledge/
│   ├── __init__.py
│   └── provider.py          # KnowledgeProvider (ABC stub, async)
└── tracing/
    ├── __init__.py
    ├── events.py            # TraceEvent
    └── trace_hook.py        # TraceHook
```

**Execution flow:**

```text
AgentExecutor.execute(agent_id, task, context?)
    → RuntimeContext (auto-created if missing)
    → ExecutionPipeline.run(context, task)
        → TraceHook.before_execute
        → [MemoryHook.before_execute]  (optional)
        → _execute_step (placeholder)
        → TraceHook.after_execute
        → [MemoryHook.after_execute]   (optional)
    → ExecutionResult
```

**Test suite:** `backend/tests/unit/runtime/` — 5 files, 30 tests.

### 1.2 Legacy Runtime (`backend/app/core/runtime/`)

**Verified structure:**

```
backend/app/core/runtime/
├── __init__.py
├── agent.py                 # Agent dataclass
├── registry.py              # AgentRegistry (in-memory)
├── runtime.py               # AgentRuntime.run()
├── executor.py              # AgentExecutor (adapter-based, async)
├── session.py, state.py
├── exceptions.py
└── adapters/
    ├── base.py
    ├── openai_adapter.py    # wraps v1 build_agent_runner
    ├── http_adapter.py
    └── plugin_adapter.py
```

**Execution flow:**

```text
HTTP POST /api/v1/runtime/agents/{id}/run
    → AgentRuntime.run(agent, input, context)
        → AgentSession + AgentState
        → core AgentExecutor.execute() (async)
            → RuntimeAdapter (openai/http/plugin)
                → v1 agent_runner factory
    → RuntimeResult
```

**Test suite:** `backend/tests/runtime/` — separate from Phase 1–6 unit tests.

### 1.3 Test verification (current run)

| Metric | Result |
|--------|--------|
| **Collected** | 30 |
| **Passed** | 30 |
| **Failed** | 0 |
| **Warning** | 1 (structlog `format_exc_info` in `test_memory_exception_does_not_fail_executor`; non-blocking) |

Commands executed:

```text
pytest backend/tests/unit/runtime/ --collect-only  → 30 collected
pytest backend/tests/unit/runtime/                 → 30 passed, 1 warning
```

No FAIL recorded. No fixes applied.

---

## 2. Dual Runtime Analysis

### 2.1 Comparison table

| 项目 | `app.runtime` | `app.core.runtime` |
|------|---------------|---------------------|
| **定位** | Phase 1–6 通用 Agent 执行基础设施（Hook + Pipeline 骨架） | Sprint 1 MVP：Agent 注册 + Adapter 桥接 v1 runner |
| **入口** | `AgentExecutor.execute(agent_id, task, context?)` | `AgentRuntime.run(agent, input, context)` |
| **调用方** | 仅 `backend/tests/unit/runtime/` 单元测试 | `backend/app/api/v1/endpoints/runtime.py` + `backend/tests/runtime/` |
| **是否生产路径** | **否** — 无 HTTP 绑定 | **条件性** — `/api/v1/runtime/*`，且 `ENABLE_RUNTIME_V2=False` 默认 503 |
| **是否 v1 依赖** | **否** | **间接** — adapters 调用 `build_agent_runner`（v1 runner），但 v1 evaluation/benchmark/celery **不 import** 此模块 |
| **Tool 系统** | `ToolRegistry`（未接入 pipeline） | 无 ToolRegistry；通过 adapter 调 v1 runner |
| **Trace** | `TraceHook` → `context.metadata["runtime_trace"]` | `trace_id` via observability; 不写 v1 traces 表 |
| **Memory** | `MemoryProvider` + `MemoryHook` | 无 |
| **未来建议** | **Future Runtime Authority（标准栈）** | **兼容层 → 逐步废弃** |

### 2.2 Current true runtime entry point

| Layer | Actual entry | Stack |
|-------|--------------|-------|
| **HTTP (when enabled)** | `POST /api/v1/runtime/agents/{id}/run` | `app.core.runtime` |
| **In-process library (tested)** | `AgentExecutor.execute()` | `app.runtime` |
| **v1 Evaluation** | `app.core.evaluation.pipeline` | Neither runtime |
| **v1 Benchmark** | `app.core.benchmark` | Neither runtime |
| **v1 Trace API/DB** | `app.api.v1.endpoints.traces` | Neither runtime |
| **Task worker / Celery** | `app.core.celery_app` | Neither runtime |

**Conclusion:** There is **no single runtime entry** today. HTTP goes to legacy; Phase 1–6 stack is library-only.

### 2.3 Import / call graph

| Module | → Runtime | Purpose |
|--------|-----------|---------|
| `app.api.v1.endpoints.runtime` | `app.core.runtime` | HTTP: create/list agents, run agent |
| `app.api.v1.router` | includes `runtime.router` at `/runtime` | Route registration |
| `app.core.runtime.*` (internal) | self-references | Adapter pipeline, registry |
| `backend/tests/runtime/*` | `app.core.runtime` | Integration tests for legacy MVP |
| `backend/tests/unit/runtime/*` | `app.runtime` | Unit tests for Phase 1–6 |
| `app.core.evaluation` | — | **No runtime import** |
| `app.core.benchmark` | — | **No runtime import** |
| `app.core.celery_app` | — | **No runtime import** |
| `app.core.agent_runner` | — | Used **by** core.runtime adapters, not vice versa |

**Zero production modules import `app.runtime` outside its own package and unit tests.**

---

## 3. Future Runtime Authority

### Decision

```text
Future Runtime Authority = app.runtime
Legacy Compatibility Layer = app.core.runtime (temporary)
```

### Rationale

| Criterion | `app.runtime` | `app.core.runtime` |
|-----------|---------------|---------------------|
| Hook extensibility (Trace/Memory/Security) | Yes | No hook model |
| Tool Registry integration path | Designed | Absent |
| Business logic isolation | Clean | Adapters embed v1 runner |
| Test coverage (Phase 1–6) | 30 focused unit tests | Separate MVP tests |
| Alignment with v2 roadmap | Primary target | Sprint 1 bridge |

`app.runtime` is the **only stack designed for long-term Agent Infrastructure** (Tool / Memory / Knowledge / Application Layer).  
`app.core.runtime` is a **thin MVP bridge** to v1 runners — valuable short-term, not the architectural center.

### Can `app.core.runtime` be directly deprecated?

**NO**

**Reasons:**

1. **HTTP API dependency:** `/api/v1/runtime/agents`, `/agents/{id}/run` call `AgentRegistry` + `AgentRuntime` exclusively.
2. **Adapter investment:** OpenAI/HTTP/Plugin adapters wrap v1 `build_agent_runner` — only path to real LLM execution today.
3. **Existing tests:** `backend/tests/runtime/` (test_api, test_runtime, test_adapter, etc.) depend on core stack.
4. **No v1 evaluation dependency:** Deprecation does **not** break evaluation/benchmark/celery — reduces migration blast radius but does not eliminate API/test work.

**Migration risk:** Medium — isolated to Runtime HTTP surface and `tests/runtime/`, not v1 evaluation core.

---

## 4. Migration Strategy

### Phase A — Freeze & parallel API (Phase 7)

**Goal:** Establish `app.runtime` as HTTP execution path without removing legacy.

| Action | Detail |
|--------|--------|
| Freeze Stable Core | `RuntimeContext`, `ExecutionResult`, `ExecutionPipeline`, `ExecutionHook`, `AgentExecutor.execute()` signature |
| Add new endpoints | `POST /runtime/execute`, `GET /runtime/executions/{id}` → **`app.runtime.AgentExecutor`** |
| Keep legacy endpoints | `/runtime/agents/*` → `app.core.runtime` (marked deprecated in docs) |
| Gate | `ENABLE_RUNTIME_V2=False` disables **both** or split flags later (`ENABLE_RUNTIME_V2_API` vs legacy) |
| No Tool HTTP | Do not expose register/list tools |

**Duration:** Phase 7 sprint.

### Phase B — Adapter bridge (post–Phase 7)

**Goal:** Real LLM/tool execution via `app.runtime` without duplicating adapter logic forever.

| Action | Detail |
|--------|--------|
| Extract adapter interface | Move or wrap `RuntimeAdapter` pattern behind `app.runtime` evolution layer |
| Pipeline `_execute_step` | Invoke adapter or ToolRegistry — first real execution |
| Legacy shim | `app.core.runtime.AgentRuntime.run()` delegates to `app.runtime.AgentExecutor` + adapter |
| Deprecation notice | Log warning on legacy HTTP endpoints |

**Duration:** 1–2 phases after Phase 7.

### Phase C — Remove legacy stack

**Goal:** Single runtime authority.

| Action | Detail |
|--------|--------|
| Remove | `backend/app/core/runtime/` |
| Migrate tests | `backend/tests/runtime/` → target `app.runtime` |
| HTTP consolidation | Single `/runtime/execute` surface |
| Config cleanup | Remove dual-flag confusion |

**Precondition:** All adapter/runner paths validated through `app.runtime`; no external consumers on legacy agent registry API.

---

## 5. Phase 7 API Boundary

### Phase 7 API Boundary Recommendation

**Expose minimal execution surface: YES**  
**Expose Tool management HTTP API: NO**

### Recommended Phase 7 endpoints

| Endpoint | Verdict | Maps to |
|----------|---------|---------|
| `POST /runtime/execute` | **Allow** | `app.runtime.AgentExecutor.execute()` |
| `GET /runtime/executions/{execution_id}` | **Allow** | Future `ExecutionStore.get()` (in-memory MVP OK) |
| `POST /runtime/tools/register` | **Reject** | Tool Provider Protocol not frozen |
| `GET /runtime/tools` | **Reject** | Exposes internal registry; tenancy/auth undefined |
| Legacy `POST /runtime/agents/{id}/run` | **Keep temporarily** | `app.core.runtime` compatibility |

### Does Runtime API depend on Tool contract?

**Phase 7: NO**

- `AgentExecutor.execute(agent_id, task, context)` accepts task string + opaque context.
- ToolRegistry is constructor-injected but **not invoked** in execution path.
- API request/response maps to `ExecutionResult` — no tool name/output fields.

### Should Tool API be delayed?

**YES**

| Reason | Impact if exposed now |
|--------|----------------------|
| Tool Provider Protocol undefined | Breaking HTTP contract when schema/versioning added |
| Registration is deploy-time concern | Sales/Support apps register tools at startup, not via public HTTP |
| Bypasses pipeline hooks | Direct tool execute skips Trace/Memory/Security hooks |
| Multi-tenant auth undefined | Enterprise API tools need tenant-scoped registry |

**Delay until:** Tool Provider Protocol frozen + `ExecutionPipeline._execute_step` invokes tools through registry.

---

## 6. Memory vs ExecutionStore Decision

### Problem statement

Current `MemoryHook` mixes two concepts:

| Operation | Key | Intended semantics |
|-----------|-----|-------------------|
| `before_execute` read | `context.metadata["memory_key"]` | Session / conversation memory |
| `after_execute` write | `context.execution_id` | Execution output archive |

**Risk:** Treating `MemoryProvider` as both session store and execution store causes:

- No round-trip test (Run 2 with `memory_key=A` cannot read Run 1 output unless something wrote to key `A`)
- Phase 7 `GET /executions/{id}` has no dedicated store — would incorrectly overload Memory
- Semantic confusion for Application Layer (CRM session vs audit log)

### Decision: **Option A**

```text
MemoryProvider     → Agent memory / session / conversation context
ExecutionStore     → execution_id → status / result / trace reference
```

**NOT Option B** (MemoryProvider also as Execution Archive).

### Rationale for Option A

| Factor | Option A (separate) | Option B (combined) |
|--------|---------------------|---------------------|
| Conceptual clarity | High | Low |
| Phase 7 execution query | Natural fit | Overloads memory keys |
| Enterprise session memory | Independent scaling (Redis) | Mixed with execution logs |
| MemoryHook fix path | Stop writing `execution_id` to MemoryProvider; use ExecutionStore | Entrench conflation |

### Phase 7 minimal ExecutionStore proposal

**Interface (evolution layer — not stable core):**

```python
class ExecutionStore(ABC):
    def save(self, execution_id: str, record: ExecutionRecord) -> None: ...
    def get(self, execution_id: str) -> ExecutionRecord | None: ...
    def update_status(self, execution_id: str, status: str) -> None: ...
```

**ExecutionRecord (minimal):**

```python
@dataclass
class ExecutionRecord:
    execution_id: str
    agent_id: str
    status: str           # SUCCESS | FAILED | RUNNING
    output: Any | None
    error: str | None
    trace_ref: dict | None  # snapshot or pointer to context.metadata["runtime_trace"]
    created_at: datetime
```

**Phase 7 MVP implementation:** `InMemoryExecutionStore` (dict, process-local) — same pattern as `InMemoryProvider`.

**MemoryHook adjustment (future phase, not Phase 6.8):**

- `before_execute`: keep `memory_key` → `MemoryProvider.get()`
- `after_execute`: **remove** `provider.set(execution_id, result)` → move to `ExecutionStore.save()`
- Optional: if session continuity desired, add explicit `provider.set(memory_key, result)` when `memory_key` present

### Memory boundary (frozen)

| Concern | Owner | Key space |
|---------|-------|-----------|
| Agent / conversation memory | `MemoryProvider` | Caller-defined `memory_key` |
| Execution status / result | `ExecutionStore` | `execution_id` |
| Runtime trace events | `RuntimeContext.metadata["runtime_trace"]` | Per execution, in-context |
| v1 evaluation trace | v1 `traces` module / DB | **Separate system — do not merge** |

---

## 7. Stable Core vs Evolution Layer

### Stable Core (freeze before Phase 7)

| Component | Freeze | Reason |
|-----------|--------|--------|
| `RuntimeContext` | **YES** | All hooks and API context carrier |
| `ExecutionResult` | **YES** | Primary API response contract |
| `AgentExecutor.execute(agent_id, task, context?)` | **YES** | Application Layer entry point |
| `ExecutionPipeline` lifecycle | **YES** | before → step → after |
| `ExecutionHook` interface | **YES** | Extension spine |
| `TraceHook` event shape | **YES** | `{type, timestamp, metadata}` in `runtime_trace.events` |

### Evolution Layer (allowed to change)

| Component | Notes |
|-----------|-------|
| Tool / ToolRegistry | Tool Provider Protocol, remote tools, schemas |
| MemoryProvider backends | Redis, SQL — not execution store |
| ExecutionStore | New in Phase 7; backends evolve |
| KnowledgeProvider + KnowledgeHook | Async/sync bridge TBD |
| `ExecutionPipeline._execute_step` | Tool loop, LLM, adapters |
| `app.core.runtime` | Deprecated compatibility layer |
| HTTP API mapping | Adapters only — not core contracts |
| Application Layer | Sales/Support agents above Runtime |
| Business adapters | CRM tools register into ToolRegistry at deploy time |

### Cross-cutting boundaries

| Domain | Stable contract | Storage | Owner module |
|--------|-----------------|---------|--------------|
| **Tool** | `Tool.execute(**kwargs)` + registry | In-process registry | `app.runtime.tools` |
| **Execution** | `ExecutionResult` | `ExecutionStore` (future) | `app.runtime.executor` |
| **Trace (Runtime)** | `TraceEvent` / `runtime_trace` | Context metadata (+ optional store ref) | `app.runtime.tracing` |
| **Trace (v1 Eval)** | v1 trace schema | DB | v1 `traces` — **do not modify** |
| **Evaluation** | v1 pipeline | DB | v1 `evaluation` — **do not modify** |

---

## 8. ExecutionResult Stability Check

### Coupling analysis

| Check | Result |
|-------|--------|
| Tool name in `ExecutionResult` | **No** |
| Tool output schema | **No** |
| Tool metadata | **No** |
| Tool execution in result | **No** |
| `tool_registry` used in `execute()` | **No** — stored on executor only |

**Current shape:**

```python
ExecutionResult(execution_id, agent_id, status, output, error)
```

### Verdict: **YES — ExecutionResult is Stable Core Contract**

**Conditions for stability:**

1. Do **not** add tool-specific fields (`tool_calls`, `tool_name`, etc.) — put in `context.metadata["runtime_trace"]` events instead.
2. Do **not** embed full trace blob in `ExecutionResult` — return `execution_id` and let client query `ExecutionStore` or optional `trace_ref`.
3. `output: Any` remains opaque — schema is Application Layer concern.

**If NO were required:** decouple by moving tool artifacts to trace events and keeping `ExecutionResult.output` as final agent answer only. Current design already satisfies this.

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Dual stack confusion | **High** | This document + Phase 7 targets `app.runtime` only for new endpoints |
| Phase 7 builds on wrong stack | **High** | Code review gate: new execute API must import `app.runtime`, not `app.core.runtime` |
| MemoryHook conflation | **Medium** | Introduce `ExecutionStore` in Phase 7; do not extend MemoryHook for execution query |
| Tool HTTP premature exposure | **Medium** | Phase 7 boundary: execute-only |
| Legacy API consumers | **Low** | Default disabled; legacy endpoints documented deprecated |
| v1 evaluation regression | **Low** | No import path from v1 to either runtime |
| Name collision (`AgentExecutor` in both stacks) | **Medium** | API layer uses explicit imports; long-term rename legacy to `CoreAgentExecutor` in Phase B |

---

## 10. Recommended Next Steps

### Immediate (Phase 7 prep)

1. **Accept boundary decision:** Future authority = `app.runtime`.
2. **Implement Phase 7 API** on `app.runtime.AgentExecutor` — `POST /runtime/execute`, `GET /runtime/executions/{id}`.
3. **Add `ExecutionStore` + `InMemoryExecutionStore`** — evolution layer, not stable core.
4. **Do not expose Tool HTTP endpoints.**
5. **Mark legacy `/runtime/agents/*` deprecated** in OpenAPI description (doc-only OK).

### Short-term (Phase 7–8)

6. Wire `ExecutionStore.save()` in executor after pipeline run (not MemoryHook).
7. Add memory round-trip e2e test once Memory vs ExecutionStore split is clear.
8. Plan adapter bridge from `app.core.runtime.adapters` to `app.runtime` pipeline step.

### Medium-term

9. Legacy shim: `app.core.runtime` delegates to `app.runtime`.
10. Remove `app.core.runtime` after migration (Phase C).

---

## Appendix A: Audit compliance

- No modifications to `backend/**`, `tests/**`, or any code files
- Only file created: `docs/v2.0/runtime-boundary-decision.md`
- Tests run read-only; failures would be recorded only (none observed)

## Appendix B: Key decisions summary

| Decision | Outcome |
|----------|---------|
| Dual Runtime | Coexist; **`app.runtime` = authority**, `app.core.runtime` = legacy compat |
| Future Runtime | **`app.runtime`** |
| ExecutionStore | **Option A** — separate from MemoryProvider |
| Memory Boundary | Session memory via `memory_key`; not execution archive |
| Phase 7 API | **Execute + execution query only**; **no Tool HTTP** |
| ExecutionResult | **Stable Core — YES** |
| Proceed to Phase 7 | **YES** (with boundaries above) |
