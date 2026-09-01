# Tool Execution Engine (Phase 8.2.1)

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 8.2.1 — Tool Execution Engine Skeleton  
**Date:** 2026-08-31

---

## 1. Architecture Diagram

### Before (Phase 8.1)

```text
AgentExecutor
      |
ToolRegistry
      |
ToolDefinition (capability metadata only)
```

### After (Phase 8.2.1)

```text
AgentExecutor
      |
ToolRegistry (capability catalog)
      |
ToolDefinition
      |
ToolExecutionEngine
      |
ToolExecutorRegistry
      |
ToolExecutorAdapter (by executor_type)
      |
[Future: LocalAdapter | RemoteAdapter | FutureProviderAdapter]
```

**Phase 8.2.1 scope:** Abstraction only — no pipeline wiring, no HTTP, no CRM.

---

## 2. ExecutorAdapter Responsibility

**File:** `backend/app/runtime/tools/adapter.py`

```python
class ToolExecutorAdapter(ABC):
    executor_type: str

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any: ...
```

| Responsibility | Owner |
|----------------|-------|
| Know `executor_type` | Adapter |
| Execute tool with arguments | Adapter |
| Know CRM/HTTP/business APIs | **NOT adapter in 8.2.1** — future concrete adapters |

Adapters are **pluggable** via `ToolExecutorRegistry`.

---

## 3. ToolExecutionEngine Responsibility

**File:** `backend/app/runtime/tools/engine.py`

| Step | Action |
|------|--------|
| 1 | Accept `ToolDefinition` + `arguments` |
| 2 | Read `tool_definition.executor_type` |
| 3 | Resolve adapter from `ToolExecutorRegistry` |
| 4 | Delegate `adapter.execute(definition, arguments)` |
| 5 | Return `ToolExecutionResult(tool_name, executor_type, output)` |

**Engine does NOT:**

- Call legacy `Tool.execute()` directly
- Contain CRM/HTTP/business logic
- Know about ToolRegistry (caller passes `ToolDefinition`)

**Errors:**

- `UnknownExecutorTypeError` — no adapter registered for type

---

## 4. ToolExecutorRegistry

**File:** `backend/app/runtime/tools/executor_registry.py`

```python
registry.register(local_adapter)   # executor_type="local"
adapter = registry.get("local")
```

| Method | Behavior |
|--------|----------|
| `register(adapter)` | One adapter per `executor_type`; duplicate → `DuplicateExecutorAdapterError` |
| `get(executor_type)` | Returns adapter or `None` |

---

## 5. Legacy Tool Migration

**Legacy path (deprecated, not core execution path):**

```text
Tool (ABC)
   |  register() with DeprecationWarning
   v
ToolDefinition (executor_type="local", metadata.legacy_tool=True)
   |
ToolExecutionEngine
   |
LocalAdapter (Phase 8.2.2 — not yet implemented)
```

**Rule:** `Tool.execute()` is **never** called by `ToolExecutionEngine`. Legacy tools become `ToolDefinition` metadata; execution routes through adapters.

---

## 6. Future Remote Adapter Plan (Phase 8.2.3+)

| Phase | Deliverable |
|-------|-------------|
| 8.2.2 | `LocalToolExecutorAdapter` — real local execution |
| 8.2.3 | `RemoteToolExecutorAdapter` — HTTP client, auth, timeout, retry, schema validation |
| 8.3 | Remote Tool Provider Protocol — endpoint, error mapping, provider registration |

**`executor_type="remote"`** in `ToolDefinition` is metadata today; execution requires registered `RemoteStubAdapter` or future implementation.

---

## 7. Phase 8.2.2 Preparation

**Ready for:** Local Tool Adapter implementation

**Tasks:**

1. Implement `LocalToolExecutorAdapter(ToolExecutorAdapter)` with `executor_type="local"`
2. Wire callable/handler resolution from `ToolDefinition.metadata`
3. Register default local adapter in engine factory (optional)
4. Unit tests for real local execution (not stub)

**Not in 8.2.2 scope:** Pipeline integration (`ExecutionPipeline._execute_step`), HTTP API changes.

---

## Appendix: Files Added (Phase 8.2.1)

| File | Purpose |
|------|---------|
| `tools/adapter.py` | `ToolExecutorAdapter` ABC |
| `tools/executor_registry.py` | `ToolExecutorRegistry` |
| `tools/engine.py` | `ToolExecutionEngine`, `ToolExecutionResult` |
| `tests/unit/runtime/test_tool_execution_engine.py` | 7 unit tests |

**Not modified:** API, core, executor, service, memory, tracing.
