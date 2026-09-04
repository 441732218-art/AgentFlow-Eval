# Runtime Boundary Decision

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 6.8 â€?Runtime Boundary Decision Audit  
**Date:** 2026-08-31  
**Type:** Read-only architecture decision audit  
**Prerequisite:** Phase 6.5 Audit (`docs/v2.0/runtime-phase6.5-audit.md`)

---

## Runtime Boundary Decision

This document freezes architectural boundaries before Phase 7 Runtime API development. It answers: which Runtime stack is authoritative, how the legacy stack is retired, and where Memory / Execution / Tool / Trace boundaries lie.

---

## 1. Current Architecture

### 1.1 Phase 1â€? Runtime (`backend/app/runtime/`)

**Verified structure (2026-08-31):**

```
backend/app/runtime/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ context.py
â”œâ”€â”€ executor/
â”?  â”œâ”€â”€ __init__.py
â”?  â””â”€â”€ executor.py          # AgentExecutor, ExecutionResult
â”œâ”€â”€ pipeline/
â”?  â”œâ”€â”€ __init__.py
â”?  â”œâ”€â”€ hooks.py             # ExecutionHook
â”?  â””â”€â”€ pipeline.py          # ExecutionPipeline
â”œâ”€â”€ tools/
â”?  â”œâ”€â”€ __init__.py
â”?  â””â”€â”€ registry.py          # Tool, ToolRegistry
â”œâ”€â”€ memory/
â”?  â”œâ”€â”€ __init__.py
â”?  â”œâ”€â”€ provider.py          # MemoryProvider (ABC)
â”?  â”œâ”€â”€ memory.py            # InMemoryProvider
â”?  â””â”€â”€ hook.py              # MemoryHook
â”œâ”€â”€ knowledge/
â”?  â”œâ”€â”€ __init__.py
â”?  â””â”€â”€ provider.py          # KnowledgeProvider (ABC stub, async)
â””â”€â”€ tracing/
    â”œâ”€â”€ __init__.py
    â”œâ”€â”€ events.py            # TraceEvent
    â””â”€â”€ trace_hook.py        # TraceHook
```

**Execution flow:**

```text
AgentExecutor.execute(agent_id, task, context?)
    â†?RuntimeContext (auto-created if missing)
    â†?ExecutionPipeline.run(context, task)
        â†?TraceHook.before_execute
        â†?[MemoryHook.before_execute]  (optional)
        â†?_execute_step (placeholder)
        â†?TraceHook.after_execute
        â†?[MemoryHook.after_execute]   (optional)
    â†?ExecutionResult
```

**Test suite:** `backend/tests/unit/runtime/` â€?5 files, 30 tests.

### 1.2 Legacy Runtime (`backend/app/core/runtime/`)

**Verified structure:**

```
backend/app/core/runtime/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ agent.py                 # Agent dataclass
â”œâ”€â”€ registry.py              # AgentRegistry (in-memory)
â”œâ”€â”€ runtime.py               # AgentRuntime.run()
â”œâ”€â”€ executor.py              # AgentExecutor (adapter-based, async)
â”œâ”€â”€ session.py, state.py
â”œâ”€â”€ exceptions.py
â””â”€â”€ adapters/
    â”œâ”€â”€ base.py
    â”œâ”€â”€ openai_adapter.py    # wraps v1 build_agent_runner
    â”œâ”€â”€ http_adapter.py
    â””â”€â”€ plugin_adapter.py
```

**Execution flow:**

```text
HTTP POST /api/v1/runtime/agents/{id}/run
    â†?AgentRuntime.run(agent, input, context)
        â†?AgentSession + AgentState
        â†?core AgentExecutor.execute() (async)
            â†?RuntimeAdapter (openai/http/plugin)
                â†?v1 agent_runner factory
    â†?RuntimeResult
```

**Test suite:** `backend/tests/runtime/` â€?separate from Phase 1â€? unit tests.

### 1.3 Test verification (current run)

| Metric | Result |
|--------|--------|
| **Collected** | 30 |
| **Passed** | 30 |
| **Failed** | 0 |
| **Warning** | 1 (structlog `format_exc_info` in `test_memory_exception_does_not_fail_executor`; non-blocking) |

Commands executed:

```text
pytest backend/tests/unit/runtime/ --collect-only  â†?30 collected
pytest backend/tests/unit/runtime/                 â†?30 passed, 1 warning
```

No FAIL recorded. No fixes applied.

---

## 2. Dual Runtime Analysis

### 2.1 Comparison table

| é¡¹ç›® | `app.runtime` | `app.core.runtime` |
|------|---------------|---------------------|
| **å®šä½** | Phase 1â€? é€šç”¨ Agent æ‰§è¡ŒåŸºç¡€è®¾æ–½ï¼ˆHook + Pipeline éª¨æž¶ï¼?| Sprint 1 MVPï¼šAgent æ³¨å†Œ + Adapter æ¡¥æŽ¥ v1 runner |
| **å…¥å£** | `AgentExecutor.execute(agent_id, task, context?)` | `AgentRuntime.run(agent, input, context)` |
| **è°ƒç”¨æ–?* | ä»?`backend/tests/unit/runtime/` å•å…ƒæµ‹è¯• | `backend/app/api/v1/endpoints/runtime.py` + `backend/tests/runtime/` |
| **æ˜¯å¦ç”Ÿäº§è·¯å¾„** | **å?* â€?æ—?HTTP ç»‘å®š | **æ¡ä»¶æ€?* â€?`/api/v1/runtime/*`ï¼Œä¸” `ENABLE_RUNTIME_V2=False` é»˜è®¤ 503 |
| **æ˜¯å¦ v1 ä¾èµ–** | **å?* | **é—´æŽ¥** â€?adapters è°ƒç”¨ `build_agent_runner`ï¼ˆv1 runnerï¼‰ï¼Œä½?v1 evaluation/benchmark/celery **ä¸?import** æ­¤æ¨¡å?|
| **Tool ç³»ç»Ÿ** | `ToolRegistry`ï¼ˆæœªæŽ¥å…¥ pipelineï¼?| æ—?ToolRegistryï¼›é€šè¿‡ adapter è°?v1 runner |
| **Trace** | `TraceHook` â†?`context.metadata["runtime_trace"]` | `trace_id` via observability; ä¸å†™ v1 traces è¡?|
| **Memory** | `MemoryProvider` + `MemoryHook` | æ—?|
| **æœªæ¥å»ºè®®** | **Future Runtime Authorityï¼ˆæ ‡å‡†æ ˆï¼?* | **å…¼å®¹å±?â†?é€æ­¥åºŸå¼ƒ** |

### 2.2 Current true runtime entry point

| Layer | Actual entry | Stack |
|-------|--------------|-------|
| **HTTP (when enabled)** | `POST /api/v1/runtime/agents/{id}/run` | `app.core.runtime` |
| **In-process library (tested)** | `AgentExecutor.execute()` | `app.runtime` |
| **v1 Evaluation** | `app.core.evaluation.pipeline` | Neither runtime |
| **v1 Benchmark** | `app.core.benchmark` | Neither runtime |
| **v1 Trace API/DB** | `app.api.v1.endpoints.traces` | Neither runtime |
| **Task worker / Celery** | `app.core.celery_app` | Neither runtime |

**Conclusion:** There is **no single runtime entry** today. HTTP goes to legacy; Phase 1â€? stack is library-only.

### 2.3 Import / call graph

| Module | â†?Runtime | Purpose |
|--------|-----------|---------|
| `app.api.v1.endpoints.runtime` | `app.core.runtime` | HTTP: create/list agents, run agent |
| `app.api.v1.router` | includes `runtime.router` at `/runtime` | Route registration |
| `app.core.runtime.*` (internal) | self-references | Adapter pipeline, registry |
| `backend/tests/runtime/*` | `app.core.runtime` | Integration tests for legacy MVP |
| `backend/tests/unit/runtime/*` | `app.runtime` | Unit tests for Phase 1â€? |
| `app.core.evaluation` | â€?| **No runtime import** |
| `app.core.benchmark` | â€?| **No runtime import** |
| `app.core.celery_app` | â€?| **No runtime import** |
| `app.core.agent_runner` | â€?| Used **by** core.runtime adapters, not vice versa |

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
| Test coverage (Phase 1â€?) | 30 focused unit tests | Separate MVP tests |
| Alignment with v2 roadmap | Primary target | Sprint 1 bridge |

`app.runtime` is the **only stack designed for long-term Agent Infrastructure** (Tool / Memory / Knowledge / Application Layer).  
`app.core.runtime` is a **thin MVP bridge** to v1 runners â€?valuable short-term, not the architectural center.

### Can `app.core.runtime` be directly deprecated?

**NO**

**Reasons:**

1. **HTTP API dependency:** `/api/v1/runtime/agents`, `/agents/{id}/run` call `AgentRegistry` + `AgentRuntime` exclusively.
2. **Adapter investment:** OpenAI/HTTP/Plugin adapters wrap v1 `build_agent_runner` â€?only path to real LLM execution today.
3. **Existing tests:** `backend/tests/runtime/` (test_api, test_runtime, test_adapter, etc.) depend on core stack.
4. **No v1 evaluation dependency:** Deprecation does **not** break evaluation/benchmark/celery â€?reduces migration blast radius but does not eliminate API/test work.

**Migration risk:** Medium â€?isolated to Runtime HTTP surface and `tests/runtime/`, not v1 evaluation core.

---

## 4. Migration Strategy

### Phase A â€?Freeze & parallel API (Phase 7)

**Goal:** Establish `app.runtime` as HTTP execution path without removing legacy.

| Action | Detail |
|--------|--------|
| Freeze Stable Core | `RuntimeContext`, `ExecutionResult`, `ExecutionPipeline`, `ExecutionHook`, `AgentExecutor.execute()` signature |
| Add new endpoints | `POST /runtime/execute`, `GET /runtime/executions/{id}` â†?**`app.runtime.AgentExecutor`** |
| Keep legacy endpoints | `/runtime/agents/*` â†?`app.core.runtime` (marked deprecated in docs) |
| Gate | `ENABLE_RUNTIME_V2=False` disables **both** or split flags later (`ENABLE_RUNTIME_V2_API` vs legacy) |
| No Tool HTTP | Do not expose register/list tools |

**Duration:** Phase 7 sprint.

### Phase B â€?Adapter bridge (postâ€“Phase 7)

**Goal:** Real LLM/tool execution via `app.runtime` without duplicating adapter logic forever.

| Action | Detail |
|--------|--------|
| Extract adapter interface | Move or wrap `RuntimeAdapter` pattern behind `app.runtime` evolution layer |
| Pipeline `_execute_step` | Invoke adapter or ToolRegistry â€?first real execution |
| Legacy shim | `app.core.runtime.AgentRuntime.run()` delegates to `app.runtime.AgentExecutor` + adapter |
| Deprecation notice | Log warning on legacy HTTP endpoints |

**Duration:** 1â€? phases after Phase 7.

### Phase C â€?Remove legacy stack

**Goal:** Single runtime authority.

| Action | Detail |
|--------|--------|
| Remove | `backend/app/core/runtime/` |
| Migrate tests | `backend/tests/runtime/` â†?target `app.runtime` |
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
- API request/response maps to `ExecutionResult` â€?no tool name/output fields.

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
- Phase 7 `GET /executions/{id}` has no dedicated store â€?would incorrectly overload Memory
- Semantic confusion for Application Layer (CRM session vs audit log)

### Decision: **Option A**

```text
MemoryProvider     â†?Agent memory / session / conversation context
ExecutionStore     â†?execution_id â†?status / result / trace reference
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

**Interface (evolution layer â€?not stable core):**

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

**Phase 7 MVP implementation:** `InMemoryExecutionStore` (dict, process-local) â€?same pattern as `InMemoryProvider`.

**MemoryHook adjustment (future phase, not Phase 6.8):**

- `before_execute`: keep `memory_key` â†?`MemoryProvider.get()`
- `after_execute`: **remove** `provider.set(execution_id, result)` â†?move to `ExecutionStore.save()`
- Optional: if session continuity desired, add explicit `provider.set(memory_key, result)` when `memory_key` present

### Memory boundary (frozen)

| Concern | Owner | Key space |
|---------|-------|-----------|
| Agent / conversation memory | `MemoryProvider` | Caller-defined `memory_key` |
| Execution status / result | `ExecutionStore` | `execution_id` |
| Runtime trace events | `RuntimeContext.metadata["runtime_trace"]` | Per execution, in-context |
| v1 evaluation trace | v1 `traces` module / DB | **Separate system â€?do not merge** |

---

## 7. Stable Core vs Evolution Layer

### Stable Core (freeze before Phase 7)

| Component | Freeze | Reason |
|-----------|--------|--------|
| `RuntimeContext` | **YES** | All hooks and API context carrier |
| `ExecutionResult` | **YES** | Primary API response contract |
| `AgentExecutor.execute(agent_id, task, context?)` | **YES** | Application Layer entry point |
| `ExecutionPipeline` lifecycle | **YES** | before â†?step â†?after |
| `ExecutionHook` interface | **YES** | Extension spine |
| `TraceHook` event shape | **YES** | `{type, timestamp, metadata}` in `runtime_trace.events` |

### Evolution Layer (allowed to change)

| Component | Notes |
|-----------|-------|
| Tool / ToolRegistry | Tool Provider Protocol, remote tools, schemas |
| MemoryProvider backends | Redis, SQL â€?not execution store |
| ExecutionStore | New in Phase 7; backends evolve |
| KnowledgeProvider + KnowledgeHook | Async/sync bridge TBD |
| `ExecutionPipeline._execute_step` | Tool loop, LLM, adapters |
| `app.core.runtime` | Deprecated compatibility layer |
| HTTP API mapping | Adapters only â€?not core contracts |
| Application Layer | Sales/Support agents above Runtime |
| Business adapters | CRM tools register into ToolRegistry at deploy time |

### Cross-cutting boundaries

| Domain | Stable contract | Storage | Owner module |
|--------|-----------------|---------|--------------|
| **Tool** | `Tool.execute(**kwargs)` + registry | In-process registry | `app.runtime.tools` |
| **Execution** | `ExecutionResult` | `ExecutionStore` (future) | `app.runtime.executor` |
| **Trace (Runtime)** | `TraceEvent` / `runtime_trace` | Context metadata (+ optional store ref) | `app.runtime.tracing` |
| **Trace (v1 Eval)** | v1 trace schema | DB | v1 `traces` â€?**do not modify** |
| **Evaluation** | v1 pipeline | DB | v1 `evaluation` â€?**do not modify** |

---

## 8. ExecutionResult Stability Check

### Coupling analysis

| Check | Result |
|-------|--------|
| Tool name in `ExecutionResult` | **No** |
| Tool output schema | **No** |
| Tool metadata | **No** |
| Tool execution in result | **No** |
| `tool_registry` used in `execute()` | **No** â€?stored on executor only |

**Current shape:**

```python
ExecutionResult(execution_id, agent_id, status, output, error)
```

### Verdict: **YES â€?ExecutionResult is Stable Core Contract**

**Conditions for stability:**

1. Do **not** add tool-specific fields (`tool_calls`, `tool_name`, etc.) â€?put in `context.metadata["runtime_trace"]` events instead.
2. Do **not** embed full trace blob in `ExecutionResult` â€?return `execution_id` and let client query `ExecutionStore` or optional `trace_ref`.
3. `output: Any` remains opaque â€?schema is Application Layer concern.

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
2. **Implement Phase 7 API** on `app.runtime.AgentExecutor` â€?`POST /runtime/execute`, `GET /runtime/executions/{id}`.
3. **Add `ExecutionStore` + `InMemoryExecutionStore`** â€?evolution layer, not stable core.
4. **Do not expose Tool HTTP endpoints.**
5. **Mark legacy `/runtime/agents/*` deprecated** in OpenAPI description (doc-only OK).

### Short-term (Phase 7â€?)

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
| ExecutionStore | **Option A** â€?separate from MemoryProvider |
| Memory Boundary | Session memory via `memory_key`; not execution archive |
| Phase 7 API | **Execute + execution query only**; **no Tool HTTP** |
| ExecutionResult | **Stable Core â€?YES** |
| Proceed to Phase 7 | **YES** (with boundaries above) |