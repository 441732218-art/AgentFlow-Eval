# Production RemoteToolClient (Phase 8.6)

## Overview

Phase 8.6 adds **`HttpRemoteToolClient`**, an HTTP transport implementation of
the frozen `RemoteToolClient` interface, plus **`CredentialResolver`** for
runtime-only secret resolution.

`InMemoryRemoteClient` remains the in-process test double. No frozen interfaces
were modified.

---

## 1. HttpRemoteToolClient Design

| Aspect | Choice |
|--------|--------|
| Interface | `RemoteToolClient.send(request) -> ToolProviderResponse` |
| HTTP library | `httpx` (already in project dependencies) |
| Method | `POST` to `request.metadata["endpoint"]` |
| Body | `{"tool_name", "arguments", "metadata"}` (metadata contains `credential_ref` only, never resolved secrets) |
| Response | JSON object matching `ToolProviderResponse` fields |
| Timeout | `timeout_seconds` constructor param (default 30.0, aligns with `RemoteExecutionPolicy`) |
| Test injection | Optional `http_client: httpx.Client` (e.g. `httpx.MockTransport`) |

### Endpoint field

`ToolProviderRequest` has **no dedicated `endpoint` field**. The adapter copies
`ToolDefinition.metadata` into `request.metadata`; HTTP client reads
`metadata["endpoint"]` (same pattern as Phase 8.5 bootstrap example tools).

---

## 2. Retry Logic Placement

### Task 1 finding

`RemoteExecutionPolicy` **is actively used** in:

`RemoteToolExecutorAdapter.execute()` (`remote_adapter.py`, lines 52â€?0)

```python
for attempt in range(1, self.policy.max_attempts + 1):
    ...
    except ToolExecutionError as exc:
        if attempt >= self.policy.max_attempts or not self.policy.is_retryable(exc):
            raise
```

### Decision: retry stays in Adapter layer

| Layer | Responsibility |
|-------|----------------|
| `RemoteToolExecutorAdapter` | Retry loop via `RemoteExecutionPolicy` |
| `HttpRemoteToolClient` | Single HTTP round-trip; raise `RemoteTimeoutError` / `RemoteProviderError` / `RemoteAuthError` |

**Why:** Adapter already owns policy + retry; Client stays transport-only.
Duplicating retry in Client would double-retry or diverge from existing Phase
8.3 tests (`test_remote_provider_policy.py`).

Default retryable errors: `RemoteTimeoutError` and message markers containing
`"timeout"` (`policy.py`).

---

## 3. CredentialResolver Design

```python
class CredentialResolver(ABC):
    def resolve(self, credential_ref: str) -> str: ...

class InMemoryCredentialResolver(CredentialResolver):
    # dict[credential_ref -> secret] â€?tests only
```

`HttpRemoteToolClient._build_headers()`:

1. Read `request.metadata["auth"]` (`auth_type`, `credential_ref`)
2. If `auth_type != "none"`, call `resolver.resolve(credential_ref)`
3. Set header (`Authorization: Bearer â€¦` or `X-API-Key: â€¦`)
4. Resolved secret exists **only in local variables** for the HTTP call

### Why secrets are not persisted

- `ToolProviderAuth.to_metadata()` exports **references only**
- Trace observation (`build_observation`) includes tool name, duration, status â€?  never headers or resolved credentials
- ExecutionRecord / logging must not store secrets (Phase 8.6 constraint)

Production should use Vault / env / cloud secret manager implementing
`CredentialResolver` â€?not `InMemoryCredentialResolver`.

---

## 4. Error Mapping

| Condition | Exception | Message shape |
|-----------|-----------|---------------|
| HTTP 401 / 403 | `RemoteAuthError` | `HTTP {code}: â€¦` (no body/headers) |
| HTTP 408 | `RemoteTimeoutError` | `HTTP 408: â€¦` |
| httpx timeout | `RemoteTimeoutError` | `HTTP request timed out ({N}s)` |
| HTTP 429 / 500 / other â‰?00 | `RemoteProviderError` | `HTTP {code}: â€¦` |
| Invalid JSON / wrong shape | `RemoteProviderError` | `HTTP {code}: invalid JSON â€¦` |
| Missing endpoint | `RemoteProviderError` | metadata must include endpoint |
| Missing resolver / ref | `RemoteAuthError` | `HTTP 401: â€¦` |

Class name **`RemoteTimeoutError`** matches `RemoteExecutionPolicy.retryable_errors`.

---

## 5. Known Limitations

| Limitation | Notes |
|------------|-------|
| No real external services in tests | `httpx.MockTransport` only |
| `InMemoryCredentialResolver` | Test/dev only |
| **Vault / env resolver** | **Required before production Application ProvideræŽ¥å…¥** â€?must implement `CredentialResolver` without storing secrets in Runtime state |
| Single POST protocol | No streaming / webhook callbacks |
| Endpoint in metadata | Not a first-class `ToolProviderRequest` field (frozen) |

### Is Vault mandatory before å¤–è´¸/ApplicationæŽ¥å…¥?

**Yes.** Application-layer remote tools need a production `CredentialResolver`
(Vault, KMS, or secure env injection). Phase 8.6 proves HTTP transport +
auth header wiring; it does **not** replace secret management infrastructure.

---

## 6. Phase 8.7+ (Application Tool Provider)

1. Application module registers `ToolDefinition` with real `metadata.endpoint`
2. Wire `HttpRemoteToolClient(credential_resolver=ProductionResolver())` into
   `create_tool_execution_engine(remote_client=...)`
3. Optionally inject into `RuntimeService` when API boundary opens
4. Provider implements JSON contract returned by mock tests

No Runtime Core changes required beyond configuration and resolver implementation.

---

## Files Added

- `backend/app/runtime/tools/credential_resolver.py`
- `backend/app/runtime/tools/http_client.py`
- `backend/tests/unit/runtime/test_http_remote_client.py`

## Files Extended

- `backend/app/runtime/tools/errors.py` â€?`RemoteAuthError`
- `backend/app/runtime/tools/__init__.py` â€?exports