# Runtime API Boundary Freeze Review

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 7.1.8 — API Boundary Freeze Review  
**Date:** 2026-08-31  
**Type:** Read-only boundary freeze (no code changes)  
**Prerequisites:** Phase 7.1, Phase 7.1.5, Phase 6.8 Boundary Decision

---

## Executive Summary

**Question:** Is Runtime Core ready to safely expose HTTP API boundaries?

**Answer:** **YES — with documented guardrails.** The in-process stack (`RuntimeService` → `AgentExecutor` → `ExecutionPipeline` → Hooks → `ExecutionStore`) is stable (45 unit tests passing). HTTP exposure has not started; Phase 7.2 must implement adapters that honor the frozen boundaries below. Legacy `app.core.runtime` HTTP routes coexist and must not be conflated with new routes.

---

## 1. RuntimeService Boundary

### 1.1 Required call chain (frozen)

```text
Runtime HTTP API (Phase 7.2)
        |
        v
RuntimeService.execute(agent_id, task, context?)
        |
        v
AgentExecutor.execute()
        |
        v
ExecutionPipeline → Hooks → ExecutionResult
        |
        v
ExecutionStore.save(ExecutionRecord)
        |
        v
ExecutionResponseDTO  →  HTTP response
```

### 1.2 Current state

| Check | Status | Evidence |
|-------|--------|----------|
| `RuntimeService.execute()` exists as service entry | **YES** | `backend/app/runtime/service/runtime_service.py` |
| Returns `ExecutionResponseDTO`, not `ExecutionResult` | **YES** | `_to_dto()` maps executor result to DTO |
| Persists via `ExecutionStore` after execute | **YES** | `_to_record()` + `save()` |
| `get_execution()` for query path | **YES** | Returns `ExecutionRecord \| None` |
| HTTP layer calls `RuntimeService` today | **NO** | `backend/app/api/` has zero imports of `app.runtime` |
| HTTP layer bypasses service (calls `AgentExecutor`) | **NO** | No API imports of `app.runtime` at all |

### 1.3 Legacy HTTP path (separate, not the Phase 7.2 target)

```text
POST /api/v1/runtime/agents/{id}/run
        |
        v
app.core.runtime.AgentRuntime.run()   ← legacy Sprint 1 MVP
```

This path **does not** use `RuntimeService`. It is gated by `ENABLE_RUNTIME_V2` but targets the wrong stack for Phase 7.2 goals.

### 1.4 Boundary verdict

| Question | Answer |
|----------|--------|
| **Does library layer satisfy `router → RuntimeService → AgentExecutor`?** | **YES** — service encapsulates executor + store |
| **Is HTTP layer compliant today?** | **N/A** — no Phase 7.2 routes exist yet |
| **Risk if Phase 7.2 skips RuntimeService** | **HIGH** — would bypass persistence, DTO mapping, future cross-cutting concerns |

### 1.5 Frozen rule for Phase 7.2

```text
ALLOW:   router.handler → RuntimeService.execute() / get_execution()
FORBID:  router.handler → AgentExecutor.execute()
FORBID:  router.handler → ExecutionStore directly
FORBID:  router.handler → app.core.runtime (for new execute/query routes)
```

---

## 2. DTO Contract

### 2.1 Current DTO (`ExecutionResponseDTO`)

**File:** `backend/app/runtime/service/dto.py`

```python
@dataclass
class ExecutionResponseDTO:
    execution_id: str
    status: str
    output: Any | None
    error: str | None
```

### 2.2 Model separation (frozen)

| Model | Layer | HTTP exposure |
|-------|-------|---------------|
| `ExecutionResult` | Executor internal | **FORBIDDEN** — executor return type only |
| `ExecutionRecord` | ExecutionStore persistence | **FORBIDDEN direct** — map via query DTO |
| `ExecutionResponseDTO` | Service → API (execute) | **ALLOWED** for `POST /runtime/execute` |

### 2.3 ExecutionResponse Contract

**ExecutionResponse Contract: YES**

**Reasons:**

1. **No internal model leakage** — DTO excludes `agent_id`, `trace_reference`, `created_at`, store internals.
2. **ExecutionStore not API-locked** — store can evolve (`ExecutionRecord` fields) if API uses adapter mapping, not raw record serialization.
3. **No Tool coupling** — DTO has zero tool name/metadata/execution fields; `RuntimeService` does not reference `ToolRegistry` in execute path.
4. **Stable minimal surface** — four fields sufficient for execute response; query endpoint needs separate DTO (see §3).

### 2.4 Gap (design action, not blocker)

Phase 7.2 should add **`ExecutionQueryDTO`** (or equivalent) for `GET /runtime/executions/{id}`:

```python
# Recommended freeze (to be created in Phase 7.2 API adapter layer)
ExecutionQueryDTO:
    execution_id: str
    status: str
    output: Any | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    # NO agent_id required in public API unless explicitly decided
    # NO trace_reference expansion into events
```

Do **not** return raw `ExecutionRecord` from HTTP handlers.

### 2.5 Risks if contract violated

| Risk | Trigger | Impact |
|------|---------|--------|
| Store schema locks API | Returning `ExecutionRecord` JSON directly | Breaking changes when store evolves |
| Executor leakage | Returning `ExecutionResult` | Exposes internal executor contract |
| Tool premature exposure | Adding tool fields to DTO before Phase 8 | API churn when Tool Provider Protocol lands |

---

## 3. Execution Query Boundary

### 3.1 Three-system separation (frozen)

| System | Owns | Must NOT own |
|--------|------|--------------|
| **ExecutionStore** | `execution_id`, `status`, `output`, `error`, lifecycle timestamps, `trace_reference` (pointer only) | `runtime_trace.events`, `memory_data`, `tool_calls`, knowledge chunks |
| **Trace (TraceHook)** | Process events in `context.metadata["runtime_trace"]` | Execution status persistence, session memory |
| **Memory (MemoryProvider / MemoryHook)** | Agent/session memory via `memory_key` | Execution lifecycle records, trace event storage |

### 3.2 Current implementation alignment

| Boundary | Clear? | Notes |
|----------|--------|-------|
| ExecutionStore vs Trace | **YES** | `trace_reference = execution_id` only; events stay in context metadata during run, not copied to store |
| ExecutionStore vs Memory | **YES** | Phase 7.1 removed `execution_id → MemoryProvider` writes; Memory uses `memory_key` only |
| ExecutionStore vs Tool | **YES** | No tool data in `ExecutionRecord` |
| Query API vs Trace | **NEEDS DISCIPLINE** | Phase 7.2 must not expose `runtime_trace.events` on GET execution |
| Query API vs Memory | **NEEDS DISCIPLINE** | Phase 7.2 must not expose `memory_data` on GET execution |

### 3.3 Recommended GET response boundary

**Include:**

- `execution_id`
- `status`
- `output`
- `error`
- `created_at`
- `updated_at`

**Exclude:**

- `runtime_trace.events`
- `memory_data`
- `tool_calls`
- `knowledge results`
- Full `ExecutionRecord.agent_id` (unless product explicitly requires — default exclude)

### 3.4 Trace reference handling

`ExecutionRecord.trace_reference` is an **opaque pointer** (currently equals `execution_id`). Phase 7.2 GET may optionally return:

```json
{ "trace_reference": "abc123" }
```

but must **not** inline trace events. Future trace query endpoint (post–Phase 7.2) resolves reference separately.

---

## 4. Feature Flag

### 4.1 Current configuration

**File:** `backend/app/config.py`

```python
ENABLE_RUNTIME_V2: bool = False
```

### 4.2 Legacy API gating

**File:** `backend/app/api/v1/endpoints/runtime.py`

- All legacy routes call `_runtime_disabled_response()`
- When `ENABLE_RUNTIME_V2=False` → HTTP 503 `{error: "runtime_disabled"}`
- When `ENABLE_RUNTIME_V2=True` → legacy agent registry/run endpoints active

### 4.3 v1 isolation verification

| System | Imports `app.runtime`? | Imports `app.core.runtime`? | Flag impact |
|--------|------------------------|----------------------------|-------------|
| v1 evaluation | No | No | None |
| v1 benchmark | No | No | None |
| Celery tasks | No | No | None |
| Existing v1 APIs | No | No | None |

### 4.4 Feature Flag Status

**Feature Flag Status: PASS (with NEED ACTION for Phase 7.2)**

**PASS because:**

- Default off (`False`)
- Legacy runtime HTTP already gated
- v1 paths unaffected

**NEED ACTION because:**

- Phase 7.2 **new** routes (`POST /runtime/execute`, `GET /runtime/executions/{id}`) must use **the same** `_runtime_disabled_response()` pattern
- Recommend reusing existing helper in `runtime.py` rather than new flag name (avoid dual-flag confusion documented in Phase 6.8)

### 4.5 Frozen rule

```text
ENABLE_RUNTIME_V2=false  →  ALL /api/v1/runtime/* including new execute/query → 503
ENABLE_RUNTIME_V2=true   →  New + legacy runtime routes available (legacy marked deprecated)
```

---

## 5. Dual Runtime Migration Boundary

### 5.1 Coexistence map

| Stack | Location | HTTP today | Phase 7.2 role |
|-------|----------|------------|----------------|
| **Runtime Core** | `app.runtime` | None | **Target for new routes** |
| **Legacy MVP** | `app.core.runtime` | `/runtime/agents/*` | **Keep, deprecate, do not modify core** |

### 5.2 Phase 7.2 bridging strategy (frozen)

**Approach:** Add new routes to existing `backend/app/api/v1/endpoints/runtime.py` (thin adapter file), wiring to `app.runtime.RuntimeService`.

```text
/runtime/execute              → RuntimeService.execute()     [NEW - app.runtime]
/runtime/executions/{id}      → RuntimeService.get_execution() [NEW - app.runtime]

/runtime/agents               → AgentRegistry               [LEGACY - app.core.runtime]
/runtime/agents/{id}/run      → AgentRuntime.run()          [LEGACY - app.core.runtime]
```

### 5.3 Constraints (frozen)

| Rule | Status |
|------|--------|
| Do not modify `backend/app/core/runtime/**` | **MANDATORY** |
| Do not migrate v1 evaluation/benchmark/celery | **MANDATORY** |
| New routes must not delegate to `AgentRuntime` | **MANDATORY** |

### 5.4 Migration risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Same `/runtime` prefix, two stacks | **High** | OpenAPI tags: `Agent Runtime (v2)` vs `Agent Runtime (legacy)` |
| Clients confuse `/agents/{id}/run` vs `/execute` | **Medium** | Document deprecated paths; execute route is canonical |
| Shared `ENABLE_RUNTIME_V2` enables both | **Low** | Acceptable for MVP; split flag only if legacy must stay on |
| Name collision (`AgentExecutor` in both packages) | **Medium** | API file imports `app.runtime.service.RuntimeService` explicitly |

---

## 6. Tool Contract Isolation

### 6.1 Phase 7.2 forbidden endpoints (frozen)

| Endpoint | Verdict | Reason |
|----------|---------|--------|
| `POST /runtime/tools/register` | **FORBIDDEN** | Tool Provider Protocol not frozen |
| `GET /runtime/tools` | **FORBIDDEN** | Exposes internal registry; tenancy undefined |
| `POST /runtime/tools/{name}/execute` | **FORBIDDEN** | Bypasses pipeline hooks |

### 6.2 Implicit Tool dependency audit

| Location | Tool dependency | Risk |
|----------|-----------------|------|
| `ExecutionResponseDTO` | None | **None** |
| `RuntimeService.execute()` | None in execute path | **None** |
| `ExecutionRecord` | None | **None** |
| `AgentExecutor.tool_registry` | Stored, **not invoked** | **Low** — constructor slot only; API must not expose registry injection over HTTP in Phase 7.2 |
| `ExecutionPipeline._execute_step` | Placeholder, no tools | **None today** |

### 6.3 Tool Contract Isolation verdict

**PASS** — Phase 7.2 DTO/Service layer is Tool-free. Phase 7.2 implementation must not add tool routes or tool fields to response schemas.

---

## 7. Phase 7.2 Readiness Decision

### 7.1 Test verification (read-only)

```text
pytest backend/tests/unit/runtime/
Result: 45 passed, 0 failed, 1 warning (structlog — non-blocking)
```

### 7.2 Proceed Phase 7.2

**Proceed Phase 7.2: YES**

**Reason:**

1. **RuntimeService** is the correct and implemented API boundary — executor + store encapsulated.
2. **ExecutionResponseDTO** is a clean, Tool-free execute contract.
3. **Memory / Execution / Trace** boundaries are separated and tested (including round-trip and failure paths in Phase 7.1.5).
4. **Feature flag** pattern exists; new routes must reuse it.
5. **Dual runtime** strategy is documented; legacy remains untouched.
6. **45/45** runtime unit tests pass — core is stable.

### 7.3 Required changes before Phase 7.2 (implementation checklist)

These are **Phase 7.2 tasks**, not blockers to starting Phase 7.2:

1. **Add HTTP adapter routes** in `endpoints/runtime.py`: `POST /execute`, `GET /executions/{execution_id}` → `RuntimeService` only.
2. **Define `ExecutionQueryDTO`** in API adapter layer; map from `ExecutionRecord` without exposing trace events or memory.
3. **Apply `_runtime_disabled_response()`** to all new routes; keep `ENABLE_RUNTIME_V2=False` default.
4. **Add API integration tests** (Phase 7.2) — unit tests alone do not cover HTTP wiring.
5. **OpenAPI deprecation markers** on legacy `/agents/*` routes.
6. **Do not add Tool HTTP endpoints** — defer to Phase 8 (Tool Provider Protocol).

### 7.4 Out of scope for Phase 7.2 (frozen)

- Tool Provider Protocol / Tool HTTP API
- Remote Tool Execution
- Database/Redis ExecutionStore backend
- CRM / Application Layer
- Modifications to `app.core.runtime`
- v1 evaluation pipeline changes

---

## Appendix A: Boundary freeze checklist

| # | Frozen boundary | Phase 7.2 compliance test |
|---|-----------------|---------------------------|
| 1 | HTTP → RuntimeService only | Code review: no `AgentExecutor` import in router |
| 2 | Execute response = ExecutionResponseDTO | OpenAPI schema matches 4 fields |
| 3 | Query response ≠ raw ExecutionRecord | Adapter maps to ExecutionQueryDTO |
| 4 | GET excludes trace events / memory | Response body inspection |
| 5 | ENABLE_RUNTIME_V2 gates all /runtime/* | Test with flag false → 503 |
| 6 | No Tool routes | Route list audit |
| 7 | Legacy routes unchanged | Diff excludes `app/core/runtime` |

## Appendix B: Audit compliance

- No modifications to `backend/app/runtime/**`, `backend/app/core/**`, `backend/app/api/**`, `backend/tests/**`
- Only file created: `docs/v2.0/runtime-api-boundary-freeze.md`
- Tests executed read-only; no fixes applied
