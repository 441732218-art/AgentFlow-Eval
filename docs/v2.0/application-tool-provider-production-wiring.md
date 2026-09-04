# Application Tool Provider Production Wiring (Phase 8.8)

## Overview

Phase 8.8 connects the Application Tool Provider layer to the **production
Runtime execution path** via `RuntimeService` â€?without modifying frozen
Runtime Core modules (`tools`, `pipeline`, `executor`, `memory`, `tracing`).

---

## Architecture

```
Application providers (applications/bootstrap.py)
        |
        v
runtime/service/tooling_bootstrap.py   â†?wiring boundary (may import applications)
        |
        +-- get_tool_registry()          (Runtime self-check tools)
        +-- get_local_handler_registry()
        +-- bootstrap_applications()
        |
        v
RuntimeService â†?AgentExecutor â†?ExecutionPipeline â†?ToolExecutionEngine
```

---

## Bootstrap Boundary (Task 1)

**Application layer** â€?explicit, no hidden globals:

```python
bootstrap_applications(registry, handler_registry)
```

**Production wiring** â€?idempotent, service-layer only:

```python
bootstrap_production_tooling()  # once per process
create_production_executor()    # registry + engine + pipeline
```

`RuntimeService()` with default constructor:

1. Calls `bootstrap_production_tooling()` (loads application tools once)
2. Builds `AgentExecutor` with `ToolExecutionEngine` wired into pipeline

Custom `executor=` injection bypasses bootstrap (existing test pattern preserved).

---

## Singleton Lifecycle (Task 3)

| Call | Behaviour |
|------|-----------|
| First `RuntimeService()` | Runtime registries init + `bootstrap_applications()` |
| Second `RuntimeService()` | `_production_tooling_bootstrapped` guard skips re-registration |
| Result | No `DuplicateToolError`; shared registry singleton |

Test helper: `reset_production_tooling()` clears flag + registry singletons.

---

## Runtime Core vs Service Boundary (Task 5)

| Layer | May import `app.applications`? |
|-------|-------------------------------|
| `runtime/tools`, `pipeline`, `executor`, `memory`, `tracing` | **No** |
| `runtime/service` | **Yes** (wiring only) |

Source scan tests exclude `runtime/service/` from leakage checks.

---

## End-to-End Path (Task 4)

Production entry (no direct `bootstrap_applications()` in test):

```python
service = RuntimeService()
definition = service.executor.tool_registry.get("app_example.echo")
context = attach_tool_request(context, definition, {"message": "..."})
dto = service.execute(agent_id=..., task=..., context=context)
# dto.output == {"app_echo": "..."}
```

Chain verified: Registry â†?Engine â†?LocalAdapter â†?Handler â†?Pipeline output.

---

## Unchanged Contracts

- `RuntimeService.execute()` signature
- `ExecutionResponseDTO`
- `ExecutionStore` / `InMemoryExecutionStore`
- Memory provider behaviour (only injected when explicitly configured)

Default non-tool execution still returns `"pipeline execution completed"`.

---

## Phase 9+ Notes

- Wire `RuntimeService` into HTTP API when boundary opens (separate phase)
- Production `CredentialResolver` for remote application tools
- Real business providers: add under `applications/<name>_provider/`, register in
  `DEFAULT_APPLICATION_PROVIDERS` â€?no Runtime Core changes