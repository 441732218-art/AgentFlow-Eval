# Remote Provider Runtime Policy (Phase 8.3)

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 8.3 — Production Remote Provider Boundary  
**Date:** 2026-08-31

---

## 1. Architecture

```text
ToolDefinition (metadata only)
        |
        v
input_schema validation
        |
        v
ToolExecutionEngine
        |
        v
RemoteToolExecutorAdapter
        |
        +-- RemoteExecutionPolicy (timeout, retry)
        +-- ToolProviderAuth (credential reference)
        |
        v
RemoteToolClient
        |
        v
ToolProviderProtocol (external)
```

---

## 2. Runtime Responsibility

### Runtime owns

| Capability | Module |
|------------|--------|
| Tool contract | `ToolDefinition`, `ToolProviderRequest/Response` |
| Input validation | `validation.py` |
| Auth reference boundary | `auth.py` |
| Execution policy | `policy.py` |
| Retry / timeout boundary | `remote_adapter.py` |
| Error mapping | `errors.py` |
| Trace-safe observation shape | `RemoteToolExecutorAdapter.build_observation()` |

### Provider owns (external)

| Capability | Owner |
|------------|-------|
| Business logic | External provider |
| External API calls | External provider |
| Credential resolution | External secret store |
| Vendor-specific retry tuning | External provider (optional) |

---

## 3. RemoteExecutionPolicy

**File:** `backend/app/runtime/tools/policy.py`

| Field | Default | Constraint |
|-------|---------|------------|
| `timeout_seconds` | `30.0` | Must be `> 0` |
| `max_retries` | `2` | `0..5` |
| `retryable_errors` | `RemoteTimeoutError`, `timeout` | Marker set for retry eligibility |

**Retry flow:**

```text
attempt 1 → failure → retryable? → attempt 2 → ...
                              └→ raise mapped ToolExecutionError
```

Non-retryable errors (e.g. `RemoteProviderError`, validation failures) are **not** retried.

---

## 4. Authentication Boundary

**File:** `backend/app/runtime/tools/auth.py`

```python
ToolProviderAuth(
    auth_type="api_key_ref",
    credential_ref="vault://provider/key",
)
```

**Allowed:** `auth_type`, `credential_ref`  
**Forbidden in Runtime storage:** `api_key`, `secret`, `token`, `password`, `authorization`

Runtime stores **references only**. Providers resolve credentials outside Runtime.

---

## 5. Schema Validation

**File:** `backend/app/runtime/tools/validation.py`

Execution order:

```text
ToolDefinition.input_schema
        |
validate_arguments(schema, arguments)
        |
RemoteToolExecutorAdapter
        |
Provider
```

Failures raise `ToolInputValidationError` before any remote call.

---

## 6. Observability Contract

Trace / observation payloads **may** include:

| Field | Description |
|-------|-------------|
| `tool_name` | Capability name |
| `executor_type` | e.g. `remote` |
| `duration_seconds` | Execution duration |
| `status` | `success` / `error` |
| `error_type` | Runtime error class name |

Trace payloads **must not** include:

- `token`
- `secret`
- `authorization`
- Customer / request payload content

Use `RemoteToolExecutorAdapter.build_observation()` as the reference shape.

---

## 7. Error Mapping

| Condition | Runtime exception |
|-----------|-------------------|
| Invalid arguments | `ToolInputValidationError` |
| Provider failure response | `RemoteProviderError` |
| Timeout exceeded | `RemoteTimeoutError` |
| Invalid provider response | `RemoteResponseValidationError` |
| Base type | `ToolExecutionError` |

Runtime does **not** propagate raw third-party exceptions.

---

## 8. Not Included (Phase 8.3)

- CRM / Email / Search business providers
- HTTP transport implementation
- OAuth flow implementation
- API key management / secret store
- Pipeline or Runtime API wiring

---

## 9. Phase 9 Preparation

After Phase 8.3, Runtime Tool capability is production-boundary complete:

```text
ToolDefinition
        |
ToolExecutionEngine
        |
+----------------+
|                |
Local Adapter    Remote Adapter
                       |
                       v
              Provider Protocol
                       |
                       v
        Production Policy Layer
        - Auth reference
        - Validation
        - Retry / Timeout
        - Observability contract
```

**Phase 9 candidates:** Security / Policy Hook integration, Evaluation Integration.

---

## Appendix: Files Added (Phase 8.3)

| File | Purpose |
|------|---------|
| `tools/policy.py` | `RemoteExecutionPolicy` |
| `tools/auth.py` | `ToolProviderAuth` |
| `tools/validation.py` | `validate_arguments()` |
| `tools/errors.py` | `ToolInputValidationError` |
| `tools/remote_adapter.py` | Policy + validation integration |
| `tests/unit/runtime/test_remote_provider_policy.py` | 8 unit tests |

**Not modified:** API, core, executor, service, memory, tracing.
