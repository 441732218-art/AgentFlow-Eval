# Tool Contract Redesign (Phase 8.1)

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 8.1 — Tool Contract Redesign  
**Date:** 2026-08-31

---

## 1. Current Tool Design Problems

Phase 2 introduced:

```python
class Tool(ABC):
    name: str
    description: str
    def execute(self, **kwargs) -> Any: ...
```

**Problems:**

| Issue | Impact |
|-------|--------|
| Assumes local Python execution | Cannot represent remote CRM/API tools as metadata-only capabilities |
| Registry stores executable objects | `list_tools()` risked exposing runtime behavior |
| No input schema | Tool Provider Protocol cannot validate arguments |
| No executor routing | Runtime cannot choose local vs remote vs future provider adapter |
| Tight coupling to `execute()` | Business systems must embed Python classes in Runtime process |

**Future target architecture:**

```text
Runtime
   |
ToolRegistry (capability metadata)
   |
Tool Provider / Executor Adapter (Phase 8.2+)
   |
Remote Service API
```

Phase 8.1 fixes the **contract layer only** — no execution, no HTTP, no CRM.

---

## 2. New ToolDefinition Model

**File:** `backend/app/runtime/tools/definition.py`

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    executor_type: str          # local | remote | future_provider
    input_schema: dict          # JSON-schema-like argument contract
    metadata: dict              # provider hints (not exposed via list_tools)
```

**Validation (`validate_tool_definition`):**

- `name` — non-empty string
- `description` — non-empty string
- `executor_type` — must be `local`, `remote`, or `future_provider`
- `input_schema` — must be `dict`
- `metadata` — must be `dict`

**Design principle:** Registration represents **capability metadata**, not executable implementation.

---

## 3. Registry Responsibility

**File:** `backend/app/runtime/tools/registry.py`

| Method | Input | Output | Notes |
|--------|-------|--------|-------|
| `register(tool)` | `ToolDefinition` (preferred) or legacy `Tool` | None | Coerces legacy → `ToolDefinition` |
| `get(name)` | `str` | `ToolDefinition \| None` | Full definition including schema/metadata |
| `list_tools()` | — | `[{name, description, executor_type}]` | **Public metadata only** |

**`list_tools()` never exposes:**

- `execute` function
- `input_schema`
- `metadata`
- runtime objects

**Internal storage:** `dict[str, ToolDefinition]` — definitions only.

---

## 4. Migration Strategy

### Compatibility Decision: **Option A — Temporarily Compatible**

| Option | Decision | Rationale |
|--------|----------|-----------|
| A. Remain temporarily compatible | **SELECTED** | Zero breakage for Phase 2 tests and `AgentExecutor.tool_registry` slot |
| B. Deprecate immediately | Partial | `Tool` emits `DeprecationWarning` on register |
| C. Remove | **Rejected** | Would break existing unit patterns before Phase 8.2 adapters exist |

**Legacy path:**

```python
registry.register(EchoTool())  # warns DeprecationWarning
# coerced to ToolDefinition(name=..., executor_type="local", metadata={"legacy_tool": True})
```

**Migration timeline:**

| Phase | Action |
|-------|--------|
| 8.1 (now) | Introduce `ToolDefinition`; registry accepts both |
| 8.2 | Introduce Tool Provider / Executor adapters using `executor_type` |
| 8.3+ | Remove legacy `Tool` registration (Option C) after adapter coverage |

**Do not delete `Tool` ABC in Phase 8.1.**

---

## 5. Phase 8.2 Preparation

Phase 8.2 will add (not in 8.1):

1. **ToolExecutorAdapter** — routes by `executor_type`:
   - `local` → in-process handler
   - `remote` → HTTP/gRPC client stub
   - `future_provider` → plugin provider slot

2. **Pipeline integration** — `ExecutionPipeline._execute_step` resolves tool via registry + adapter (no API change).

3. **Trace events** — optional `tool.invoked` in `runtime_trace` (not HTTP DTO).

**Frozen boundaries (unchanged from Phase 7.3):**

- No `/runtime/tools` HTTP endpoints
- No changes to `ExecutionResponseDTO` / `ExecutionQueryDTO`
- No CRM/Sales/Email business code in Runtime

---

## Appendix: Files Changed (Phase 8.1)

| File | Change |
|------|--------|
| `backend/app/runtime/tools/definition.py` | New `ToolDefinition` + validation |
| `backend/app/runtime/tools/registry.py` | Redesigned registry |
| `backend/app/runtime/tools/__init__.py` | Export new types |
| `backend/tests/unit/runtime/test_tool_registry.py` | Updated + new coverage |

**Not modified:** API, core runtime, executor, service, memory, tracing.
