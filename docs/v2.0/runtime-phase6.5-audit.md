# Runtime Phase 6.5 Audit

**Project:** AgentFlow Intelligence v2.0  
**Scope:** `backend/app/runtime/` (Phase 0–6)  
**Audit type:** Read-only architecture audit  
**Date:** 2026-08-31  
**Auditor role:** Senior AI Infrastructure Architect  

---

## 1. Current Runtime Status

### 1.1 Directory inventory

All expected Phase 1–6 directories under `backend/app/runtime/` exist and contain implementation code (not empty placeholders).

| Module | Path | Current state | Issues | Recommendation |
|------|------|---------------|--------|----------------|
| **Root** | `__init__.py` | Public export surface for Runtime types | Does not export `KnowledgeProvider`; dual-runtime not documented here | Keep as stable public API; document coexistence with `app.core.runtime` |
| **Context** | `context.py` | `RuntimeContext(execution_id, agent_id, metadata)` dataclass | `metadata` is untyped bag; no schema for reserved keys | **Freeze** shape; document reserved keys (`runtime_trace`, `memory_key`, `memory_data`) |
| **Executor** | `executor/executor.py` | `AgentExecutor.execute()` → pipeline → `ExecutionResult` | `tool_registry` stored but **never used** in execution path | Keep injection slot; wire in later phase behind evolution layer |
| **Pipeline** | `pipeline/pipeline.py`, `hooks.py` | Lifecycle: `before_execute` → `_execute_step` (stub) → `after_execute` | `_execute_step` is hard-coded placeholder; no tool/LLM loop | **Freeze** hook contract; evolve `_execute_step` only |
| **Tools** | `tools/registry.py` | `Tool` ABC + `ToolRegistry` (register/get/list_tools) | No remote tool adapter; no JSON schema on tools | Keep registry; extend via adapters (Option B) |
| **Memory** | `memory/provider.py`, `memory.py`, `hook.py` | `MemoryProvider` ABC + `InMemoryProvider` + `MemoryHook` | **Asymmetric keys** (read `memory_key`, write `execution_id`); no round-trip e2e test | Document semantics as dual-purpose; add e2e test in Phase 7+ |
| **Knowledge** | `knowledge/provider.py` | `KnowledgeProvider` async ABC only | No implementation, no hook, no integration; **async/sync mismatch** with Memory | Evolution layer only; add `KnowledgeHook` when implementing |
| **Tracing** | `tracing/events.py`, `trace_hook.py` | `TraceEvent` + `TraceHook` writing to `metadata["runtime_trace"]` | In-memory only; not linked to v1 trace DB | **Freeze** event append semantics |

### 1.2 Critical architectural finding: dual Runtime stacks

The repository currently contains **two independent Runtime implementations**:

| Stack | Location | Wired to HTTP API? | Tests |
|-------|----------|-------------------|-------|
| **Phase 1–6 Runtime** | `backend/app/runtime/` | **No** | `backend/tests/unit/runtime/` (30 tests) |
| **Sprint 1 MVP Runtime** | `backend/app/core/runtime/` | **Yes** — `/api/v1/runtime/*` via `endpoints/runtime.py` | `backend/tests/runtime/` |

- `ENABLE_RUNTIME_V2: bool = False` in `backend/app/config.py` gates the **core/runtime HTTP API**, not `app/runtime/` directly.
- `router.py` includes `runtime.router` at prefix `/runtime` pointing to `app.core.runtime`, not `app.runtime`.

**Implication:** Phase 0–6 work is a **clean-room infrastructure layer** with solid unit-test coverage, but it is **not yet the live API runtime**. Phase 7 must explicitly decide whether to bridge `app/runtime` → HTTP or converge with `app/core/runtime`.

### 1.3 Phase 0–6 completion assessment

| Phase | Claimed scope | Verified in code | Verdict |
|-------|---------------|------------------|---------|
| Phase 0 | Git / format hygiene | Staged `router.py`, `config.py`; runtime files use LF, no BOM observed in audited files | Partially complete (repo-wide hygiene still dirty; see Git Status) |
| Phase 1 | Directory skeleton | All dirs present | **Complete** |
| Phase 2 | Tool Registry | Full implementation + 7 tests | **Complete** |
| Phase 3 | Agent Executor | `ExecutionResult`, `execute()` lifecycle | **Complete** |
| Phase 4 | Execution Pipeline + Hook | Pipeline + hook injection | **Complete** |
| Phase 5 | Runtime Trace Hook | `TraceHook` auto-injected in default pipeline | **Complete** |
| Phase 6 | Memory Provider | `InMemoryProvider`, `MemoryHook`, executor integration | **Complete** (with semantic gap noted below) |

**Overall:** Phase 1–6 MVP skeleton is **functionally complete as an in-process library**, with a clear hook-based extension model. It is **not yet enterprise-ready** (no persistence, no remote tools, no security policy, no API bridge for this stack).

---

## 2. Test Verification

### 2.1 Collection

```text
Command: pytest backend/tests/unit/runtime/ --collect-only
Result:  30 tests collected in 0.09s
```

### 2.2 Execution

```text
Command: pytest backend/tests/unit/runtime/
Result:  30 passed, 0 failed, 1 warning in 0.20s
```

| Metric | Count |
|--------|-------|
| Collected | 30 |
| PASS | 30 |
| FAIL | 0 |

### 2.3 Test file breakdown

| File | Tests |
|------|-------|
| `test_executor.py` | 5 |
| `test_memory.py` | 7 |
| `test_pipeline.py` | 6 |
| `test_tool_registry.py` | 7 |
| `test_trace_hook.py` | 5 |

### 2.4 Warning (non-failure)

- `test_memory_exception_does_not_fail_executor` triggers structlog `UserWarning` about `format_exc_info` in processor chain. Does not affect PASS/FAIL.

### 2.5 Test coverage gaps (audit findings, not failures)

| Gap | Risk |
|-----|------|
| No **memory round-trip e2e** (write under `execution_id`, read under `memory_key`) | Medium — semantic bug could ship undetected |
| No Knowledge tests | Expected — layer not implemented |
| No integration test linking `app/runtime` to HTTP API | High for Phase 7 — two stacks untested together |
| `tool_registry` injection tested but execution path never invokes tools | Low — intentional skeleton state |

---

## 3. Tool Architecture Review

### 3.1 Current Tool model

```python
class Tool(ABC):
    name: str
    description: str
    def execute(self, **kwargs: Any) -> Any: ...
```

`ToolRegistry`: `register(tool)`, `get(name) → Tool | None`, `list_tools() → [{name, description}]`

### 3.2 Strengths

- **Simple lifecycle:** register once, resolve by name, invoke synchronously.
- **Easy to test:** pure Python, no I/O required for unit tests.
- **Clear Runtime boundary:** business systems implement `Tool` and register; Runtime does not embed CRM/Sales logic.
- **Metadata separation:** `list_tools()` returns metadata only, not executable objects — safer for future API exposure patterns.

### 3.3 Limitations for enterprise Agent Runtime

| Future need | Current support | Gap |
|-------------|-----------------|-----|
| Local Python Tool | Yes | None |
| HTTP Remote Tool | No | Need `RemoteTool` adapter implementing `Tool.execute()` |
| External Service Tool | No | Need timeout, auth, circuit breaker wrappers |
| Enterprise API Tool | No | Need schema validation, tenancy, audit hooks |
| Tool input/output schema | No | `**kwargs` is untyped; no JSON Schema / OpenAPI binding |
| Async tools | No | `execute()` is sync only |
| Tool versioning | No | Duplicate name rejected; no version suffix strategy |

### 3.4 Migration options

#### Option A — Retain current design (recommended)

**Approach:** Keep `Tool` + `ToolRegistry` as stable core. Add adapter classes:

- `LocalTool(Tool)` — current pattern
- `HttpRemoteTool(Tool)` — wraps HTTP call inside `execute()`
- `ServiceTool(Tool)` — wraps gRPC/message bus

**Pros:** Zero breaking change; existing 7 registry tests remain valid; adapters are additive.  
**Cons:** `Tool.execute(**kwargs)` stays loosely typed; schema validation must live in adapters or a future `ToolDefinition` layer.  
**Risk:** Low if adapters are kept outside stable core.

#### Option B — Progressive migration

**Approach:** Introduce `ToolDefinition` / `ToolProvider` protocol alongside existing `Tool`. Registry accepts both via wrapper:

```text
ToolProvider → adapts to → Tool (legacy)
```

**Compatibility:** `register()` overload or `register_provider()` new method.  
**Migration cost:** Medium — 2 registration paths during transition.  
**Test impact:** Add adapter tests; existing tests unchanged.

#### Option C — Complete replacement

**Approach:** Remove `Tool` ABC, replace with LangChain-style or OpenAI function-calling schema registry.

**Pros:** Richer schema from day one.  
**Cons:** Breaks Phase 2 contract; rewrites tests; violates incremental v2 principle.  
**Risk:** High — unnecessary at MVP stage.

**Recommendation:** **Option A now**, with **Option B elements** (e.g. `register_provider()`) when Tool Provider Protocol is defined. Do **not** delete or rewrite `ToolRegistry`.

---

## 4. ExecutionResult Coupling Review

### 4.1 Current ExecutionResult shape

```python
@dataclass
class ExecutionResult:
    execution_id: str
    agent_id: str
    status: Literal["SUCCESS", "FAILED"]
    output: Any | None
    error: str | None
```

### 4.2 Tool coupling analysis

| Coupling type | Present? | Location | Risk |
|---------------|----------|----------|------|
| Tool name in result | No | — | None |
| Tool output schema | No | — | None |
| Tool metadata | No | — | None |
| Tool execution in pipeline | No | `_execute_step` returns constant string | None |
| ToolRegistry on executor | **Storage only** | `AgentExecutor.__init__` sets `self.tool_registry` | **Low** — unused field, no behavioral coupling |

**Conclusion:** `ExecutionResult` is **decoupled from Tool system**. Stable core is clean.

**Future risk:** If `output` later embeds tool call traces directly (instead of via `RuntimeContext.metadata`), coupling could emerge. Recommend keeping tool call details in `context.metadata["runtime_trace"]` events (e.g. `tool.invoked`, `tool.completed`) rather than expanding `ExecutionResult`.

---

## 5. Memory Architecture Review

### 5.1 Current MemoryHook behavior

**before_execute:**

```text
memory_key = context.metadata.get("memory_key")
if memory_key:
    value = provider.get(memory_key)
    context.metadata["memory_data"] = value
```

**after_execute:**

```text
provider.set(context.execution_id, result)
```

### 5.2 Key asymmetry analysis

| Operation | Key used | Semantics |
|-----------|----------|-----------|
| Read | `metadata["memory_key"]` | Caller-supplied session / logical key |
| Write | `context.execution_id` | Per-execution archive key |

This is **Situation A: two different purposes**, not a bug per se:

1. **Session Memory** — caller sets `memory_key="session-abc"` to load prior session state.
2. **Execution Archive** — each run stores output under unique `execution_id` for audit/replay.

### 5.3 Problem

**No test proves cross-execution session continuity:**

```text
Run 1: memory_key=A → writes to execution_id=E1 (not A)
Run 2: memory_key=A → reads A → None (unless something else wrote to A)
```

Current tests validate:

- Hook reads when key pre-populated in provider (`test_memory_hook_before_reads_existing_value`)
- Hook writes under `execution_id` (`test_memory_hook_after_saves_result_by_execution_id`)

They do **not** validate: *Run 1 output is readable on Run 2 via `memory_key=A`*.

### 5.4 Recommendation

1. **Document explicitly** in Memory layer: read path = session key; write path = execution archive.
2. **Phase 7+:** Add optional `write_back_memory_key: bool` or separate `SessionMemoryHook` vs `ExecutionArchiveHook`.
3. **Required test (future):**

   ```text
   Run 1: memory_key="A", execute → provider["E1"] = result
   Run 2: memory_key="A" → expect ??? (define intended behavior first)
   ```

4. If session continuity is desired, **after_execute should also** `provider.set(memory_key, result)` when `memory_key` is present.

**Do not change in this audit phase** — record as known semantic gap.

---

## 6. Knowledge Layer Review

### 6.1 Current state

```python
class KnowledgeProvider(ABC):
    async def query(self, query: str, *, top_k: int = 5) -> list[dict[str, Any]]: ...
```

- No concrete implementation (`InMemoryKnowledgeProvider` missing).
- `knowledge/__init__.py` exports nothing.
- Not injected into `AgentExecutor` or `ExecutionPipeline`.
- **Async interface** while Memory/Tool/Pipeline are **sync** — integration friction.

### 6.2 Future enterprise support

| Future backend | Supported by current interface? | Notes |
|----------------|--------------------------------|-------|
| Vector Database | Partially | `query()` + `list[dict]` chunks is RAG-friendly |
| Enterprise KB | Partially | Needs tenant/filter params on `query()` |
| Document Retrieval | Partially | Needs source URI, chunk id in return dict convention |
| RAG Pipeline | No | No `KnowledgeHook`; no injection into `context.metadata` |

### 6.3 KnowledgeHook recommendation

**Yes — add in a future phase**, mirroring `MemoryHook`:

```text
before_execute:
  if task or metadata["knowledge_query"]:
    chunks = await/sync knowledge_provider.query(...)
    context.metadata["knowledge_context"] = chunks
```

Consider sync wrapper or async pipeline variant before hook implementation.

**Status:** Evolution layer — safe to defer until after Phase 7 API boundary is frozen.

---

## 7. Phase 7 API Boundary Recommendation

### 7.1 Current HTTP state

Existing `/api/v1/runtime/*` (when `ENABLE_RUNTIME_V2=True`):

- Uses `app.core.runtime` (Agent registry, AgentRuntime.run)
- Endpoints: create/list agents, run agent
- Does **not** expose `app.runtime.AgentExecutor`, ToolRegistry, or MemoryHook

### 7.2 Should Phase 7 expose Tool API?

**Recommendation: NO — not in initial Phase 7.**

| Endpoint (avoid now) | Risk |
|---------------------|------|
| `POST /runtime/tools/register` | Locks HTTP contract to current `Tool` ABC before Tool Provider Protocol |
| `GET /runtime/tools` | Exposes internal registry; tenancy/auth undefined |
| `POST /runtime/tools/{name}/execute` | Bypasses pipeline hooks (trace, memory, security) |

Tool registration is an **Application Layer / deployment-time** concern (Sales AI registers CRM tools at startup), not a public multi-tenant HTTP surface at MVP.

### 7.3 Recommended Phase 7 surface (for `app/runtime` stack)

Expose only **execution orchestration**, not internal contracts:

| Endpoint | Purpose | Expose? |
|----------|---------|---------|
| `POST /runtime/execute` | `{agent_id, task, context?}` → `ExecutionResult` + trace | **Yes** |
| `GET /runtime/executions/{execution_id}` | Status / result query (in-memory or future store) | **Yes** (minimal) |
| `GET /runtime/health` | Runtime v2 liveness | Optional |

Response may **include** `context.metadata.runtime_trace` for observability; do **not** expose raw `ToolRegistry` or allow arbitrary tool registration over HTTP.

### 7.4 Bridge strategy

Phase 7 must resolve dual-stack ambiguity:

1. **Preferred:** New thin API adapter calls `app.runtime.AgentExecutor` (Phase 1–6 stack).
2. **Interim:** Keep `app.core.runtime` API deprecated/frozen; document migration path.
3. **Avoid:** Merging two stacks without explicit adapter — creates two sources of truth.

---

## 8. Stable Core vs Evolution Layer

### 8.1 Stable Core (freeze before Phase 7)

| Component | Freeze? | Reason |
|-----------|---------|--------|
| `RuntimeContext` | **Yes** | Universal execution carrier; hooks depend on it |
| `ExecutionResult` | **Yes** | API response contract foundation |
| `ExecutionPipeline` lifecycle | **Yes** | `before → step → after` is extension spine |
| `ExecutionHook` interface | **Yes** | Trace/Memory/Security all plug in here |
| `AgentExecutor.execute(agent_id, task, context?)` | **Yes** | Primary entry point for Application Layer |
| `TraceHook` event append format | **Yes** | Observability consumers will depend on shape |

### 8.2 Evolution Layer (allow change)

| Component | Evolution allowed | Reason |
|-----------|-------------------|--------|
| `Tool` / `ToolRegistry` | Yes | Remote tools, schemas, providers |
| `MemoryProvider` backends | Yes | Redis, SQL, vector store |
| `KnowledgeProvider` + hook | Yes | Not yet implemented |
| `ExecutionPipeline._execute_step` | Yes | Tool loop, LLM planner go here |
| `AgentExecutor` optional deps | Yes | Add `knowledge_provider`, security policy |
| Application Layer | Yes | Sales/Support agents above Runtime |
| HTTP API mapping | Yes | Adapter layer, not core |

### 8.3 Boundary diagram

```text
┌─────────────────────────────────────────────┐
│           Application Layer (future)         │
│     Sales AI / Support AI / Research AI      │
└─────────────────────┬───────────────────────┘
                      │ execute(task)
┌─────────────────────▼───────────────────────┐
│              STABLE CORE                     │
│  AgentExecutor → ExecutionPipeline → Hooks   │
│  RuntimeContext / ExecutionResult            │
└─────────────────────┬───────────────────────┘
                      │ uses
┌─────────────────────▼───────────────────────┐
│           EVOLUTION LAYER                    │
│  ToolRegistry | MemoryProvider | Knowledge   │
│  Remote adapters | SecurityHook | RAG          │
└─────────────────────────────────────────────┘
```

---

## 9. Future Dependency Analysis

### 9.1 Readiness matrix

| Future capability | Current foundation | Blocker | Dependency order |
|-------------------|---------------------|---------|------------------|
| **Tool Provider Protocol** | `Tool` ABC + registry | No schema/versioning | After core freeze; extend registry (Option A/B) |
| **Remote Tool Execution** | Sync `execute()` | No HTTP adapter | Tool adapter → pipeline step |
| **Security Policy Hook** | `ExecutionHook` base | Not implemented | Add `SecurityHook` in pipeline; no core change |
| **Knowledge Provider** | Async ABC stub | No hook, sync/async mismatch | KnowledgeHook → pipeline before_execute |
| **Evaluation Integration** | v1 evaluation untouched | No bridge | Application/eval adapter calls v1 APIs post-run |
| **Application Extension** | Executor + registry slots | No Application Layer dir | Apps register tools + call executor |

### 9.2 Blocking points

1. **Dual runtime stacks** — Phase 7 API target must be chosen explicitly.
2. **Pipeline `_execute_step` stub** — no tool/LLM invocation yet; enterprise runtime incomplete until evolved.
3. **Memory key semantics** — session vs archive undefined for cross-run continuity.
4. **No persistence** — execution status query requires store (even in-memory TTL cache) for real API.
5. **Knowledge async/sync split** — pipeline is sync; async providers need bridge.

### 9.3 Risk summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Two runtime implementations diverge | High | Document + bridge plan in Phase 7 |
| Premature Tool HTTP API | Medium | Expose execute-only |
| Memory semantic confusion | Medium | Document + e2e test |
| Business logic leaks into Runtime | Medium | Enforce Application Layer boundary (already clean in Phase 1–6) |
| v1 evaluation regression | Low | `app/runtime` isolated from v1 paths |

### 9.4 Keeping AgentFlow generic (not a business system)

Current Phase 1–6 code **passes** the generic infrastructure test:

- No CRM/Sales/Email imports in `app/runtime/`
- Tools referenced only as examples in docstrings (`crm.search_customer`)
- Hooks and providers are domain-agnostic
- Business systems integrate via **Tool registration** and **Application Layer** (future), not Runtime internals

**Guardrail for Phase 7+:** HTTP adapters must not accept arbitrary tool registration from external callers; tools loaded at deploy time by application modules.

---

## 10. Recommended Next Steps

### 10.1 Immediate (before Phase 7 coding)

1. **Freeze Stable Core interfaces** listed in §8.1 — document in `docs/v2.0/runtime-stable-core.md` (future doc, not this audit).
2. **Decide API target stack:** `app/runtime` vs convergence with `app/core/runtime`.
3. **Document Memory semantics** (session key vs execution archive) and plan e2e test.

### 10.2 Phase 7 scope (recommended)

1. Add HTTP adapter: `POST /runtime/execute` → `AgentExecutor` (`app/runtime`).
2. Gate with `ENABLE_RUNTIME_V2=False` (existing flag).
3. Return `ExecutionResult` + optional `runtime_trace` from context.
4. **Do not** expose Tool register/list HTTP endpoints.
5. Add minimal execution status query (in-memory dict acceptable for MVP).

### 10.3 Post–Phase 7

1. Implement `KnowledgeHook` + sync bridge for `KnowledgeProvider`.
2. Evolve `_execute_step` to invoke `ToolRegistry` (with trace events).
3. Add `SecurityPolicyHook` stub.
4. Memory round-trip e2e test + optional session write-back.
5. Remote tool adapter (`HttpRemoteTool`) without changing `ToolRegistry` core.

### 10.4 Proceed to Phase 7?

**YES** — with conditions:

- Phase 1–6 provides sufficient **hook-based, test-covered skeleton** for long-term evolution.
- Phase 7 must be **API adapter + execute boundary only**, not Tool HTTP or CRM.
- Dual-stack decision must be made explicit on day one of Phase 7.

---

## Appendix A: Files audited

```
backend/app/runtime/
├── __init__.py
├── context.py
├── executor/
│   ├── __init__.py
│   └── executor.py
├── pipeline/
│   ├── __init__.py
│   ├── hooks.py
│   └── pipeline.py
├── tools/
│   ├── __init__.py
│   └── registry.py
├── memory/
│   ├── __init__.py
│   ├── provider.py
│   ├── memory.py
│   └── hook.py
├── knowledge/
│   ├── __init__.py
│   └── provider.py
└── tracing/
    ├── __init__.py
    ├── events.py
    └── trace_hook.py
```

## Appendix B: Audit constraints compliance

- No modifications to `backend/app/**` or `backend/tests/**`
- Only file created: `docs/v2.0/runtime-phase6.5-audit.md`
- No code fixes applied despite identified gaps (by design)
