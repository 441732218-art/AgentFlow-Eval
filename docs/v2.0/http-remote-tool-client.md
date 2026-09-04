# HttpRemoteToolClient (Phase 9.2)

## Architecture

```
ToolDefinition (metadata.endpoint)
        |
RemoteToolExecutorAdapter  â†?RemoteExecutionPolicy (retry / timeout guard)
        |
HttpRemoteToolClient       â†?single HTTP round-trip per send()
        |
External Provider (HTTP POST)
```

Application providers (e.g. trade) register remote tool **definitions** only.
Transport is Runtime responsibility; business logic stays external.

---

## HTTP Protocol Contract

**Endpoint:** `ToolProviderRequest.metadata["endpoint"]`  
(from `ToolDefinition.metadata` via adapter)

**Method:** `POST`

**Request body:**

```json
{
  "name": "tool.name",
  "arguments": {},
  "metadata": {}
}
```

**Success response (HTTP 2xx):**

```json
{
  "success": true,
  "output": {},
  "metadata": {}
}
```

**Failure response (HTTP 2xx body):**

```json
{
  "success": false,
  "error": "message"
}
```

â†?`HttpRemoteToolClient` raises `RemoteProviderError`.

---

## Responsibilities

### HttpRemoteToolClient DOES

| Responsibility | Detail |
|----------------|--------|
| HTTP transport | httpx POST |
| Serialization | JSON request/response |
| Response parsing | Map to `ToolProviderResponse` |
| Error mapping | Runtime exception types only |

### HttpRemoteToolClient DOES NOT

- Business logic (CRM, email, search)
- Authentication policy decisions (uses `ToolProviderAuth` refs only)
- Retry loops (adapter + `RemoteExecutionPolicy`)
- Vault / secret management (`CredentialResolver` is optional, later phase)

---

## RemoteExecutionPolicy Integration

| Layer | Role |
|-------|------|
| `RemoteToolExecutorAdapter` | Retry via `max_attempts` / `is_retryable()` |
| `HttpRemoteToolClient` | Single attempt; httpx timeout from policy default |

Factory helper:

```python
client = create_http_remote_tool_client(remote_policy=RemoteExecutionPolicy())
engine = create_tool_execution_engine(remote_client=client, remote_policy=policy)
```

Unit tests continue using `InMemoryRemoteClient`.

---

## Error Mapping

| Situation | Runtime Error |
|-----------|---------------|
| Connection / HTTP transport failure | `RemoteProviderError` |
| Timeout (httpx / HTTP 408) | `RemoteTimeoutError` |
| Invalid JSON / missing `success` / bad schema | `RemoteResponseValidationError` |
| Provider body `success: false` | `RemoteProviderError` |
| HTTP 401 / 403 | `RemoteAuthError` |

External types (`httpx.*`, `JSONDecodeError`) are never exposed in messages.

---

## Credential Boundary

Allowed in metadata:

```python
{"auth": {"auth_type": "bearer_ref", "credential_ref": "vault://trade/provider"}}
```

Forbidden in persisted metadata:

- `api_key`, `token`, `secret`, `password`

Optional `CredentialResolver` resolves refs at request time only (test double:
`InMemoryCredentialResolver`). Production Vault integration is a later phase.

---

## Factory Usage

```python
from app.runtime.tools import (
    HttpRemoteToolClient,
    create_http_remote_tool_client,
    create_tool_execution_engine,
)

http_client = create_http_remote_tool_client()
engine = create_tool_execution_engine(remote_client=http_client)
```

---

## Future Flow (Trade Example)

```
trade.search_customer
    â†?RemoteToolExecutorAdapter
    â†?HttpRemoteToolClient
    â†?External Trade Service HTTP endpoint
```

Requires `metadata.endpoint` on the tool definition and a production
`CredentialResolver` â€?not part of Phase 9.2.

---

## Related Docs

- `production-remote-tool-client.md` â€?Phase 8.6 initial implementation notes
- `remote-tool-provider-protocol.md` â€?request/response dataclasses
- `trade-application-provider.md` â€?Application layer template