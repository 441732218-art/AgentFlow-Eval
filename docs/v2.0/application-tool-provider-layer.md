# Application Tool Provider Layer (Phase 8.7)

## Overview

Phase 8.7 introduces the **Application Tool Provider Layer** — a boundary where
business systems register tools into Runtime without modifying Runtime Core.

Runtime Core remains frozen. All application code lives under
`backend/app/applications/`.

---

## 1. Application Provider Contract

```python
class ApplicationToolProvider(ABC):
    def register_tools(
        self,
        registry: ToolRegistry,
        handler_registry: LocalHandlerRegistry,
    ) -> None: ...
```

| Principle | Detail |
|-----------|--------|
| Dependency direction | Application → Runtime public types only |
| No Runtime → Application imports | Runtime never imports `applications/**` |
| Explicit registries | `bootstrap_applications(registry, handler_registry)` receives instances — does not require mutating globals |
| Test isolation | Use `create_tool_registry(bootstrap=False)` + fresh `LocalHandlerRegistry()` |

Orchestrator: `backend/app/applications/bootstrap.py`

```python
DEFAULT_APPLICATION_PROVIDERS = [ExampleApplicationToolProvider()]

def bootstrap_applications(registry, handler_registry) -> None:
    for provider in DEFAULT_APPLICATION_PROVIDERS:
        provider.register_tools(registry, handler_registry)
```

No auto-discovery / plugin scanning in Phase 8.7.

---

## 2. Relationship to Phase 8.5 Runtime Self-Check Examples

Two **independent** example tool sets coexist by design:

| Source | Tool names | Purpose | Loaded by |
|--------|------------|---------|-----------|
| `runtime/tools/bootstrap.py` | `example.echo`, `example.remote_search` | Runtime self-check / unit tests | `get_tool_registry()` / `create_tool_registry(bootstrap=True)` |
| `applications/example_provider/` | `app_example.echo`, `app_example.remote_search` | Application registration pattern demo | `bootstrap_applications()` only |

### Why they do not conflict

1. **Different names** — `DuplicateToolError` (Phase 8.5) would fire if both
   used `example.echo` on the same registry.
2. **Different bootstrap paths** — Runtime tests never call
   `bootstrap_applications()`.
3. **Optional composition** — Production wiring may call both bootstraps on the
   same registry instance when both tool sets are desired (verified in tests).

Task 0 conclusion: Application layer uses **`app_example.*`** prefix.

---

## 3. Example Provider Layout

```
backend/app/applications/example_provider/
├── __init__.py
├── tools.py       # ToolDefinition list (app_example.*)
├── handlers.py    # Local Python callables
└── bootstrap.py   # ExampleApplicationToolProvider
```

---

## 4. Future Real Business Integration

To add a future business system (e.g. trade/export application):

1. Create `backend/app/applications/<business>_provider/`
2. Implement `ApplicationToolProvider.register_tools()`
3. Define `ToolDefinition` entries with business-specific names (not in Runtime)
4. Register local handlers and/or remote endpoints in metadata
5. Add provider instance to `DEFAULT_APPLICATION_PROVIDERS` in
   `applications/bootstrap.py`
6. At app startup (future Phase): wire registries and call
   `bootstrap_applications(registry, handler_registry)`

**Do not** modify `backend/app/runtime/**` frozen modules.

---

## 5. Core Promise Verification

| Claim | Verified? |
|-------|-----------|
| Runtime tests pass with zero Application code | ✅ `pytest backend/tests/unit/runtime/` unchanged |
| Runtime source has no `applications` imports | ✅ scan test |
| Application tools execute via Engine/Adapter | ✅ e2e tests |
| New business = new provider directory only | ✅ by design |

**Conclusion:** Adding a business tool provider requires only Application-layer
code + orchestrator registration — **no Runtime Core changes**.

---

## 6. Phase 9+ Notes

- Wire `bootstrap_applications()` into production startup alongside
  `get_tool_registry()` when RuntimeService integration is approved
- Implement production `CredentialResolver` (Vault) for remote application tools
- HTTP endpoint exposure for tools remains out of scope until API boundary opens
