# Tool Registry Lifecycle (Phase 8.5)

## Overview

Phase 8.5 adds **lifecycle management** for `ToolRegistry`: a static bootstrap
source, process-wide singleton access, explicit lookup failures, and verified
local/remote execution paths using example tools only.

Frozen components (`ToolDefinition`, `ToolExecutionEngine`, adapters, pipeline)
were not modified.

---

## 1. Registration Model

### Static startup registration, read-only at runtime

Tools are registered from an explicit Python module:

`backend/app/runtime/tools/bootstrap.py`

```python
DEFAULT_TOOL_DEFINITIONS = [
    ToolDefinition(name="example.echo", executor_type="local", ...),
    ToolDefinition(name="example.remote_search", executor_type="remote", ...),
]
```

On first call to `get_tool_registry()`, the singleton loads this list via
`bootstrap_tool_definitions()`.

**Why no dynamic register/unregister in production?**

| Concern | Static bootstrap | Dynamic runtime registration |
|--------|------------------|------------------------------|
| Predictability | Tool set fixed at startup | Tool set changes mid-flight |
| Security / audit | One code-reviewed list | Arbitrary code can add tools |
| Scope | Runtime Core stays business-agnostic | Marketplace / plugin concerns |

Dynamic `register()` remains on `ToolRegistry` for **unit tests** that need
isolated instances (`create_tool_registry(bootstrap=False)`).

### Singleton vs MemoryProvider singleton

Both use lazy process-wide singletons, but semantics differ:

| Component | Kind | Mutable at runtime? | Purpose |
|-----------|------|---------------------|---------|
| `ToolRegistry` | Configuration | No (after bootstrap) | Which tools exist |
| `LocalHandlerRegistry` | Configuration | No (after bootstrap) | Local callable bindings |
| `MemoryProvider` | State | Yes | Per-execution memory |

Registry holds **capability metadata**; MemoryProvider holds **execution
state**. Sharing the singleton *pattern* does not mean sharing lifecycle rules.

---

## 2. Local Handler Binding

Local tools resolve handlers through `LocalHandlerRegistry`:

1. `bootstrap.py` defines `DEFAULT_LOCAL_HANDLERS` â€?a `dict` of tool name â†?   **function reference** (e.g. `example_echo_handler`).
2. `get_local_handler_registry()` bootstraps handlers on first access.
3. `LocalToolExecutorAdapter` calls
   `handler_registry.get(tool_definition.name)` and invokes
   `handler(**arguments)`.

No dynamic import (`importlib` string paths). Handlers are plain Python
callables registered at startup â€?the same static model as tool definitions.

Missing local handler â†?`MissingLocalHandlerError` (unchanged, adapter layer).

Missing tool definition â†?`ToolNotFoundError` (registry layer, Phase 8.5).

---

## 3. Remote Provider Verification

### Example remote tool

`example.remote_search` uses `executor_type="remote"` (frozen contract; not
`"http"`). HTTP endpoint URL lives in `metadata["endpoint"]` for documentation
and future transport wiring:

```python
metadata={
    "endpoint": "http://mock.test/tools/invoke",
    "provider_id": "example-mock-provider",
}
```

### Verified chain (unit tests)

```
get_tool_registry()
  â†?registry.get("example.remote_search")
  â†?ToolExecutionEngine.execute(definition, args)
  â†?RemoteToolExecutorAdapter (executor_type="remote")
  â†?InMemoryRemoteClient (test mock; simulates external provider)
  â†?ToolProviderResponse â†?result.output
```

### Conclusion: future Application Layer integration

**Yes â€?with configuration-only changes at the Application boundary.**

To connect an external system (e.g. a future trade/export application) as a
remote tool provider:

1. Add a `ToolDefinition` with `executor_type="remote"` and provider metadata
   (endpoint, auth) in bootstrap or a future app-level bootstrap extension.
2. Configure a `RemoteToolClient` implementation that calls that endpoint.
3. No changes to `ToolExecutionEngine`, adapters, or pipeline are required.

Runtime Core remains unaware of any specific business domain.

**Caveat:** This phase validates the chain with `InMemoryRemoteClient` only.
Real HTTP transport (production `RemoteToolClient`) is a later wiring task, not
a Runtime contract change.

---

## 4. Lookup Semantics

| Method | Missing tool |
|--------|--------------|
| `ToolRegistry.get(name)` | Raises `ToolNotFoundError` |
| `ToolRegistry.register(name)` duplicate | Raises `DuplicateToolError` (no silent overwrite) |

Duplicate registration fails loudly so misconfigured bootstrap lists surface at
startup rather than silently replacing production tools.

---

## 5. Known Limitations

- Example tools only (`example.*` prefix); no business tools in Runtime Core.
- Bootstrap is not wired into `RuntimeService` / HTTP API (forbidden in Phase 8.5).
- Remote path tested with in-memory mock, not live HTTP.
- `executor_type="future_provider"` reserved; no adapter yet.

---

## 6. Extension Points (Phase 9+)

| Extension | Location | Notes |
|-----------|----------|-------|
| Application tool bootstrap | App layer module | Import and call `registry.register()` at app startup, or extend bootstrap list |
| Production RemoteToolClient | Infrastructure / app wiring | HTTP client reading `metadata["endpoint"]` |
| Marketplace / dynamic tools | Future phase | Requires policy, auth, and unregister semantics â€?out of scope for 8.5 |
| RuntimeService integration | Phase 9+ | Inject `get_tool_registry()` + engine into executor when API boundary opens |

---

## API Summary

```python
from app.runtime.tools import (
    get_tool_registry,
    get_local_handler_registry,
    create_tool_registry,
    reset_tool_registry,  # tests only
    ToolNotFoundError,
)
```