# Local Tool Adapter (Phase 8.2.2)

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 8.2.2 â€?Local Tool Executor Adapter  
**Date:** 2026-08-31

---

## 1. Local Adapter Architecture

```text
ToolDefinition (capability metadata)
      |
      v
ToolExecutionEngine
      |
      v
ToolExecutorRegistry
      |
      v
LocalToolExecutorAdapter  (executor_type="local")
      |
      v
LocalHandlerRegistry
      |
      v
Python callable
```

**Phase 8.2.2 scope:** Local execution only. No HTTP, CRM, remote clients, or pipeline wiring.

---

## 2. Handler Registry Responsibility

**File:** `backend/app/runtime/tools/local_handler_registry.py`

| Method | Behavior |
|--------|----------|
| `register(name, handler)` | Bind a Python callable to a tool name |
| `get(name)` | Return callable or `None` |

**Validation:**

- Empty name â†?`ValueError`
- Non-callable handler â†?`TypeError`
- Duplicate name â†?`DuplicateLocalHandlerError`
- Missing handler at execution â†?`MissingLocalHandlerError`

The handler registry is **separate** from `ToolRegistry`. Capability metadata and executable handlers are registered independently.

---

## 3. Why ToolDefinition Does Not Contain Callable

`ToolDefinition` stores **what** a tool is (name, description, schema, executor routing):

```python
ToolDefinition(
    name="math.add",
    description="Add two numbers",
    executor_type="local",
    input_schema={...},
    metadata={...},
)
```

It does **not** store:

- `execute` field
- `callable` / `handler` reference
- function pointers

**Rationale:**

| Concern | Benefit of separation |
|---------|----------------------|
| Serialization | Definitions can cross API/process boundaries |
| Remote tools | Same contract for `executor_type="remote"` without local code |
| Security | Execution surface is explicit via handler registry |
| Testing | Swap handlers without changing definitions |

Execution is resolved at runtime:

```text
definition.name  â†? LocalHandlerRegistry.get(name)  â†? handler(**arguments)
```

---

## 4. Legacy Migration Path

**Deprecated (not core path):**

```text
Tool (ABC)
   |  ToolRegistry.register() + DeprecationWarning
   v
ToolDefinition (executor_type="local", metadata.legacy_tool=True)
```

**Execution (core path):**

```text
register_legacy_tool_handler(handler_registry, tool_instance)
   |
   v
LocalHandlerRegistry["tool.name"] = tool.execute
   |
   v
LocalToolExecutorAdapter â†?handler(**arguments)
```

**Rule:** `ToolExecutionEngine` never calls `Tool.execute()` directly. Legacy tools work when both:

1. Definition is registered (or coerced) in `ToolRegistry`
2. Handler is registered in `LocalHandlerRegistry` via `register_legacy_tool_handler()`

Direct `Tool.execute()` remains valid for backward-compatible tests but is not the runtime execution path.

---

## 5. Default Engine Factory

**File:** `backend/app/runtime/tools/factory.py`

```python
engine = create_default_tool_execution_engine(handler_registry)
```

Registers:

```text
"local" â†?LocalToolExecutorAdapter
```

Does **not** register remote or future adapters.

---

## 6. Future Remote Adapter Preparation

| Phase | Deliverable |
|-------|-------------|
| 8.2.2 âœ?| `LocalToolExecutorAdapter` + `LocalHandlerRegistry` |
| 8.2.3 / 8.3 | `RemoteToolExecutorAdapter` + Tool Provider Protocol |

**Remote path (future):**

```text
ToolDefinition (executor_type="remote")
      |
      v
RemoteToolExecutorAdapter
      |
      v
Tool Provider Protocol (endpoint, auth, timeout, retry, schema validation, error mapping)
      |
      v
External Service
```

Local and remote adapters share the same `ToolExecutionEngine` routing; complexity stays out of Runtime Core.

---

## Appendix: Files Added (Phase 8.2.2)

| File | Purpose |
|------|---------|
| `tools/local_handler_registry.py` | `LocalHandlerRegistry`, legacy handler helper |
| `tools/local_adapter.py` | `LocalToolExecutorAdapter` |
| `tools/factory.py` | `create_default_tool_execution_engine()` |
| `tests/unit/runtime/test_local_tool_adapter.py` | 8 unit tests |

**Not modified:** API, core, executor, service, memory, tracing.