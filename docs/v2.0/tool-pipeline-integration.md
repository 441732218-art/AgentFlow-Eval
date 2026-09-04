# Tool Pipeline Integration (Phase 8.4)

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 8.4 â€?ToolExecutionEngine â†?ExecutionPipeline Integration  
**Date:** 2026-08-31

---

## 1. Architecture

```text
RuntimeService          (frozen)
       |
       v
AgentExecutor           (minimal context metadata extension)
       |
       v
ExecutionPipeline       (Phase 8.4 primary change)
       |
       +-- before_hooks (TraceHook, MemoryHook â€?unchanged order)
       +-- execute_step
       |      |
       |      +-- no tool â†?default stub output
       |      +-- tool_definition present â†?ToolExecutionEngine.execute()
       +-- after_hooks (unchanged order)
       |
       v
ToolExecutionEngine     (frozen since Phase 8.2â€?.3)
       |
       +----------------+
       |                |
 Local Adapter     Remote Adapter
```

---

## 2. Tool Request on RuntimeContext

Tool requests are attached via **metadata** (no `RuntimeContext` schema change):

| Metadata key | Type | Purpose |
|--------------|------|---------|
| `tool_definition` | `ToolDefinition` | Capability to execute |
| `tool_arguments` | `dict` | Invocation arguments |

Helpers: `backend/app/runtime/executor/context_fields.py`

```python
attach_tool_request(context, tool_definition, tool_arguments)
get_tool_definition(context)
get_tool_arguments(context)
```

---

## 3. ToolExecutionEngine Mandatory Entry

**Rule:** `ExecutionPipeline` must **not** call:

- `LocalHandlerRegistry`
- `RemoteToolClient`
- legacy `Tool.execute()`

All tool execution flows through:

```text
ToolDefinition
    â†?ToolExecutionEngine.execute()
    â†?Adapter
```

Implementation: `backend/app/runtime/pipeline/tool_step.py`

---

## 4. Hook Lifecycle Protection

Pipeline lifecycle is **unchanged**:

```text
before_hooks
    â†?execute_step
    â†?after_hooks
    â†?return result â†?AgentExecutor â†?ExecutionResult
```

Hook order must not be modified to accommodate tools. Tool execution happens **inside** `execute_step` only.

---

## 5. Frozen Boundaries (Phase 8.4)

| Component | Status |
|-----------|--------|
| `RuntimeService` | Unchanged |
| `ExecutionStore` | Unchanged |
| `MemoryProvider` / `MemoryHook` | Unchanged |
| `TraceHook` | Unchanged |
| `ExecutionResult` | Unchanged |
| Runtime API DTO | Unchanged |
| `ToolExecutionEngine` | Unchanged |

---

## 6. Default Behavior (No Tool Request)

When `context.metadata` has no `tool_definition`:

```python
return "pipeline execution completed"
```

Existing unit tests, API tests, and memory round-trip tests remain valid.

---

## 7. Not Included (Phase 8.4)

- LLM function calling
- CRM / Email business tools
- Tool HTTP API (`/runtime/tools`)
- Tool Registry lifecycle management (Phase 8.5)
- `ExecutionResult` schema changes

---

## 8. Phase 8.5 Preparation

Next: Tool Registry lifecycle â€?register definitions + handlers at service bootstrap, resolve tool by name in pipeline.

---

## Appendix: Files Changed (Phase 8.4)

| File | Purpose |
|------|---------|
| `pipeline/tool_step.py` | Engine-only tool step |
| `pipeline/pipeline.py` | Optional `tool_execution_engine` injection |
| `executor/context_fields.py` | Minimal tool metadata helpers |
| `tests/unit/runtime/test_pipeline_tool_execution.py` | 8 integration tests |

**Not modified:** API, service, memory, tracing, core/runtime.