# Runtime API Stabilization Review

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 7.3 — Runtime API Stabilization & Boundary Verification  
**Date:** 2026-08-31  
**Type:** Read-only audit + stabilization tests (no business code changes)

---

## 1. Current Runtime Flow

### 1.1 Phase 7.2 canonical execute/query path

```text
POST /api/v1/runtime/execute
GET  /api/v1/runtime/executions/{execution_id}
        |
        v
runtime.py (HTTP Adapter)
  - ENABLE_RUNTIME_V2 gate (_runtime_disabled_response)
  - Request validation (RuntimeExecuteRequest)
  - RuntimeContext builder (optional context dict)
  - DTO serialization (_execution_response_to_dict / ExecutionQueryDTO map)
        |
        v
RuntimeService (singleton via get_runtime_service)
  - execute(agent_id, task, context?) → ExecutionResponseDTO
  - get_execution(execution_id) → ExecutionRecord | None
        |
        v
AgentExecutor.execute()
        |
        v
ExecutionPipeline.run()
  - TraceHook (runtime_trace events → context.metadata)
  - MemoryHook (optional, memory_key session memory)
  - _execute_step (placeholder)
        |
        v
ExecutionStore.save(ExecutionRecord)
  - InMemoryExecutionStore (dict, process-local)
```

### 1.2 Legacy path (unchanged, separate stack)

```text
POST /api/v1/runtime/agents/{agent_id}/run
GET  /api/v1/runtime/agents
POST /api/v1/runtime/agents
        |
        v
app.core.runtime (AgentRegistry + AgentRuntime)
```

---

## 2. Stable Contract Decision

### 2.1 Part 1 — API Contract Audit

#### POST `/api/v1/runtime/execute` — Execute Response

**Verified fields (exact):**

| Field | Present |
|-------|---------|
| `execution_id` | YES |
| `status` | YES |
| `output` | YES |
| `error` | YES |

**Verified absent from response body:**

| Field | Absent |
|-------|--------|
| `agent_id` | YES |
| `tool` / `tool_output` / `tool_calls` | YES |
| `trace_events` / `runtime_trace` | YES |
| `memory_data` | YES |
| `trace_reference` | YES |
| Internal metadata | YES |

**Implementation:** `_execution_response_to_dict()` maps only four DTO fields (`runtime.py:86-92`).

#### GET `/api/v1/runtime/executions/{execution_id}` — Query Response

**Verified fields (exact):**

| Field | Present |
|-------|---------|
| `execution_id` | YES |
| `status` | YES |
| `output` | YES |
| `error` | YES |
| `created_at` | YES (ISO string) |
| `updated_at` | YES (ISO string) |

**Verified not directly exposed:**

| Internal model | Exposed raw? |
|----------------|--------------|
| `ExecutionRecord` | NO — mapped via `execution_record_to_query_dto()` |
| `RuntimeContext` | NO |
| `TraceEvent` / `runtime_trace.events` | NO |
| `MemoryProvider` data | NO |

**Note:** `ExecutionRecord.agent_id` and `trace_reference` exist in store but are **stripped** at API boundary.

### 2.2 Contract freeze decisions

| Contract | Frozen? | Verdict |
|----------|---------|---------|
| **Runtime API (execute + query shapes)** | **YES** | Four-field execute + six-field query stable for Phase 8+ |
| **ExecutionResponseDTO** | **YES** | Matches execute response exactly |
| **ExecutionQueryDTO** | **YES** | Matches query response (timestamps as ISO strings at HTTP layer) |

### 2.3 Part 2 — Runtime Boundary Audit

| Path | Exists? | Location | Risk |
|------|---------|----------|------|
| `endpoint → RuntimeService` | **YES** | `runtime_execute`, `runtime_get_execution` | **Expected** |
| `endpoint → AgentExecutor` | **NO** | — | None |
| `endpoint → ExecutionStore` | **NO** | — | None |
| `endpoint → MemoryProvider` | **NO** | — | None |
| `endpoint → TraceHook` | **NO** | — | None |
| `RuntimeService → AgentExecutor` | YES | service layer | Expected |
| `RuntimeService → ExecutionStore` | YES | service layer | Expected |

**HTTP adapter imports:** `RuntimeService`, `ExecutionResponseDTO`, `execution_record_to_query_dto`, `RuntimeContext` (request mapping only). No executor/store/memory imports in endpoint module.

### 2.4 Part 3 — Feature Flag Audit

**Config:** `ENABLE_RUNTIME_V2: bool = False` (default)

| Condition | POST `/execute` | GET `/executions/{id}` | RuntimeService called? | ExecutionStore write? |
|-----------|-----------------|------------------------|------------------------|----------------------|
| `ENABLE_RUNTIME_V2=False` | 503 `runtime_disabled` | 503 `runtime_disabled` | **NO** (early return) | **NO** |
| `ENABLE_RUNTIME_V2=True` | 200 execute response | 200 / 404 query | **YES** | **YES** |

**Legacy `app.core.runtime` routes:** Still present at `/runtime/agents/*`; same flag gate; **not replaced, not modified** in Phase 7.2/7.3.

### 2.5 Part 4 — ExecutionStore Boundary Audit

**ExecutionStore owns:**

- Execution lifecycle (`execution_id`)
- Status (`SUCCESS` / `FAILED`)
- Final result (`output`, `error`)
- Timestamps (`created_at`, `updated_at`)
- Opaque `trace_reference` (internal, not in API response)

**ExecutionStore does NOT own:**

- Session/agent memory (`MemoryProvider`)
- Trace event timeline (`TraceHook` / `runtime_trace`)
- Tool execution history

**Backend swap path (future):**

```text
InMemoryExecutionStore → RedisExecutionStore → DatabaseExecutionStore
```

**Requires changes:** ExecutionStore implementation only (+ DI wiring in `get_runtime_service` factory, future phase).

**Does NOT require changes:** `RuntimeService` public methods, `ExecutionResponseDTO`, `ExecutionQueryDTO`, HTTP response shapes.

### 2.6 Part 5 — Memory / Trace Isolation Verification

| System | Owns | Does NOT own |
|--------|------|--------------|
| **Memory** | `memory_key` session read/write via `MemoryHook` | `execution_id` archive (removed Phase 7.1), execution query |
| **Trace** | `runtime_trace.events` on `RuntimeContext.metadata` during run | Execution status/result in store |
| **ExecutionStore** | Persisted execution lifecycle | Trace events, memory blobs |

**Phase 7.1.5 verified:** Memory round-trip across two `RuntimeService.execute()` calls; failure path does not corrupt session memory.

---

## 3. Phase 8 Readiness

### Can enter Phase 8 (Tool Provider Protocol)?

**YES — with constraints**

| Question | Answer |
|----------|--------|
| Does current Tool affect API? | **NO** — DTOs and HTTP responses have zero tool fields |
| Must Runtime API change for Phase 8? | **NO** — tools integrate inside `ExecutionPipeline._execute_step` and evolution layer |
| Tool HTTP API needed in Phase 8? | **NO** — defer `/runtime/tools*` until protocol frozen |

**Phase 8 work stays inside:**

- `app.runtime.tools` (Tool Provider Protocol)
- `ExecutionPipeline._execute_step` (tool invocation)
- Optional trace events (`tool.invoked`) in `runtime_trace` — **not** in HTTP DTO

---

## 4. Remaining Risks

| Risk | Severity | Notes |
|------|----------|-------|
| **InMemory Store** | Medium | Process restart loses executions; acceptable for MVP; document for operators |
| **Feature Flag shared** | Low | Single `ENABLE_RUNTIME_V2` gates legacy + new routes; intentional for MVP |
| **Legacy Runtime coexistence** | Medium | `/agents/{id}/run` vs `/execute` may confuse clients; document canonical path |
| **Trace persistence** | Medium | Trace events not queryable via GET execution; future trace endpoint needed |
| **Tool integration** | Low (if Phase 8 respects boundaries) | Risk only if tool fields leak into DTO — currently clean |
| **Singleton RuntimeService** | Low | Shared store across requests in one process; correct for in-memory MVP |
| **output: Any** | Low | Opaque output may embed arbitrary JSON from future tools; contract is field name not schema |

---

## 5. Stabilization Tests Added (Phase 7.3)

**File:** `backend/tests/api/runtime/test_runtime_api_stabilization.py`

| Test | Purpose |
|------|---------|
| `test_runtime_api_execute_response_contract_snapshot` | Execute response exact 4-key contract |
| `test_execution_query_isolation_from_trace_and_memory` | Query exact 6-key contract; no trace/memory |
| `test_feature_flag_isolation_blocks_execute_and_query_without_side_effects` | Flag OFF → 503 both routes; empty store |
| `test_runtime_service_boundary_regression_http_handlers_use_service_only` | Handlers use service only; no core imports |

---

## 6. Test Verification (read-only run)

```text
pytest backend/tests/unit/runtime/  → 45 passed
pytest backend/tests/api/runtime/   → 10 passed (5 Phase 7.2 + 4 Phase 7.3 + shared)
Total runtime-related:               → 50 passed, 0 failed
```

---

## 7. Phase 7.3 Conclusion

| Decision | Outcome |
|----------|---------|
| Runtime API frozen | **YES** |
| ExecutionResponseDTO frozen | **YES** |
| ExecutionQueryDTO frozen | **YES** |
| Phase 8 ready | **YES** |
| Business code modified in 7.3 | **NO** |

Runtime API contract is stable enough to freeze. Phase 8 Tool Provider Protocol can proceed without changing HTTP shapes, provided tool integration remains inside the pipeline evolution layer.

---

## Appendix: Audit compliance

- No modifications to `backend/app/runtime/**`, `backend/app/api/**`, `backend/app/core/**`
- Files created: `docs/v2.0/runtime-api-stabilization.md`, `backend/tests/api/runtime/test_runtime_api_stabilization.py`
- Test failures: none recorded
