# Trade Application Provider Template (Phase 9.1)

## Overview

Phase 9.1 adds **`trade_provider`** — a template for future trade/export
customer-acquisition systems to register tools with Runtime **without modifying
Runtime Core**.

This phase defines contracts and mock handlers only. No CRM, email delivery,
database, or real external integration.

---

## 1. Why Trade Belongs in the Application Layer

| Concern | Application Layer | Runtime Core |
|---------|-------------------|--------------|
| Business tool names (`trade.*`) | ✅ | ❌ |
| Domain input schemas | ✅ | ❌ |
| Mock / real business logic | ✅ | ❌ |
| Tool execution routing | ❌ | ✅ |
| Adapter protocol | ❌ | ✅ |

Runtime answers: *how* tools execute. Applications answer: *what* tools exist
and *what* they mean for a business domain.

---

## 2. Why Runtime Core Does Not Know Trade

Production wiring (`runtime/service/tooling_bootstrap.py`) calls
`bootstrap_applications()` with generic registries. Runtime Core modules
(`tools`, `pipeline`, `executor`, `memory`, `tracing`) never import
`trade_provider` or reference `trade.*` tool names.

Source scan tests enforce this boundary.

---

## 3. Trade Provider Structure

```
backend/app/applications/trade_provider/
├── __init__.py
├── schemas.py      # TypedDict input contracts
├── tools.py        # ToolDefinition list
├── handlers.py     # Mock local handlers
└── bootstrap.py    # TradeApplicationProvider
```

Registered via `DEFAULT_APPLICATION_PROVIDERS` in
`applications/bootstrap.py`.

---

## 4. Tool Definitions

| Name | executor_type | Handler | Purpose |
|------|---------------|---------|---------|
| `trade.search_customer` | remote | — (definition only) | Customer search contract |
| `trade.generate_email` | local | mock draft generator | Email draft contract |
| `trade.create_followup` | remote | — (definition only) | Follow-up task contract |

Remote tools register **definitions only**. Remote client wiring is a later
phase (HTTP provider + credentials).

---

## 5. Adding a New Business Provider

1. Create `backend/app/applications/<business>_provider/`
2. Implement `ApplicationToolProvider.register_tools()`
3. Define `ToolDefinition` entries with a unique namespace prefix
   (e.g. `trade.*`, not bare `search_customer`)
4. Register local handlers in `LocalHandlerRegistry` where
   `executor_type="local"`
5. Add provider instance to `DEFAULT_APPLICATION_PROVIDERS`

**No Runtime Core changes required.**

Example layout:

```
applications/
    example_provider/    # Phase 8.7 demo (app_example.*)
    trade_provider/      # Phase 9.1 trade template (trade.*)
    <future>_provider/   # Your business system
```

---

## 6. Execution Chain (Verified)

```
TradeApplicationProvider.register_tools()
    → bootstrap_applications()
    → ToolRegistry / LocalHandlerRegistry
    → ToolExecutionEngine
    → LocalToolExecutorAdapter (trade.generate_email)
    → RemoteToolExecutorAdapter (remote definitions, when client wired)
```

---

## 7. Out of Scope (Later Phases)

- CredentialResolver / Vault
- Real CRM or email provider HTTP endpoints
- Marketplace / dynamic registry
- HTTP API exposure
- Database persistence

---

## 8. Core Promise

**Adding trade (or any business) tools requires only a new Application Provider
directory + bootstrap registration. Runtime Core remains unchanged.**
