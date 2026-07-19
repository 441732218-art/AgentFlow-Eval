# AgentFlow-Eval API Contract v1（Freeze）

| 属性 | 值 |
|------|-----|
| **Base path** | `/api/v1` |
| **Version** | **v1 frozen** (2026-07-19) |
| **Auth** | Optional API Key (`X-API-Key` / `Authorization: Bearer`) when `AUTH_ENABLED=true` |
| **Tenant** | Optional `X-Tenant-ID` when `MULTI_TENANT_ENABLED=true` |
| **Machine contract** | [`openapi-v1.json`](./openapi-v1.json) |
| **Compat check** | `python -m scripts.export_openapi --check` / `tests/unit/test_api_contract.py` |

> **Freeze rule**: paths + methods in this document and `openapi-v1.json` must not break.  
> Additive fields/endpoints are allowed; renames/removals require v2.

---

## 1. Common

### 1.1 Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | if AUTH on | API key secret |
| `Authorization: Bearer <key>` | alt | Same as API key |
| `X-Tenant-ID` | if multi-tenant scoped | Tenant UUID or slug |
| `X-Request-ID` | no | Client correlation id |

### 1.2 Error shape

```json
{
  "error": {
    "code": 401,
    "message": "Unauthorized",
    "detail": "Provide a valid X-API-Key ..."
  },
  "request_id": "..."
}
```

| HTTP | Meaning |
|------|---------|
| 400 | Bad request |
| 401 | Unauthorized (missing/invalid key) |
| 403 | Forbidden (RBAC / tenant membership) |
| 404 | Not found (or hidden cross-tenant) |
| 402 | Quota / billing (when billing on) |
| 409 | Conflict (e.g. tenant slug) |
| 422 | Validation |
| 429 | Rate limit / (future) QUOTA_EXCEEDED |
| 500 | Server error |

### 1.3 Permissions

See [rbac-enterprise.md](./rbac-enterprise.md). Endpoint-level `@require_permission` applies when `AUTH_ENABLED` and `RBAC_ENABLED`.

---

## 2. Health（outside `/api/v1`）

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | public | Composite health |
| GET | `/health/live` | public | Liveness |
| GET | `/health/ready` | public | Readiness (DB/Redis) |
| GET | `/metrics` | public* | Prometheus |

---

## 3. Me

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/v1/me` | none (identity) | actor, role, permissions, tenant, deploy |
| GET | `/api/v1/me/permissions` | none | permissions only |

**Response (me)** example:

```json
{
  "actor": "admin",
  "role": "system_admin",
  "permissions": ["task:read", "..."],
  "rbac_enforced": true,
  "auth_enabled": true,
  "multi_tenant_enabled": false,
  "tenant": {},
  "deploy": {"profile": "private"}
}
```

---

## 4. Tenants（enterprise）

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/v1/tenants/context` | — | Resolved tenant context |
| GET | `/api/v1/tenants` | tenant:manage **or** task:read | List visible tenants |
| POST | `/api/v1/tenants` | tenant:create | Create tenant (+ creator as tenant_admin) |
| GET | `/api/v1/tenants/{id}` | task:read | Get tenant (member) |
| GET | `/api/v1/tenants/{id}/members` | tenant:manage **or** task:read | List members |
| POST | `/api/v1/tenants/{id}/members` | tenant:manage | Add/update member |

**POST /tenants** request:

```json
{ "name": "Acme Corp", "slug": "acme", "plan_id": null }
```

---

## 5. Tasks

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/v1/tasks` | task:read | List (actor + tenant filter) |
| POST | `/api/v1/tasks` | task:create | Create (`tenant_id` from header) |
| GET | `/api/v1/tasks/{id}` | task:read | Detail |
| DELETE | `/api/v1/tasks/{id}` | task:delete | Delete |
| POST | `/api/v1/tasks/{id}/execute` | task:execute | Run evaluation |
| POST | `/api/v1/tasks/{id}/cancel` | task:cancel | Cancel |
| POST | `/api/v1/tasks/{id}/archive` | task:update | Archive |
| POST | `/api/v1/tasks/{id}/unarchive` | task:update | Unarchive |
| POST | `/api/v1/tasks/{id}/test-suites` | task:update | Add suite |
| POST | `/api/v1/tasks/{id}/test-suites/upload` | task:update | Upload suites |

**POST /tasks** request:

```json
{
  "name": "eval-demo",
  "description": "",
  "agent_config": { "model": "gpt-4o-mini" }
}
```

---

## 6. Traces / Reports / Diagnosis / Dashboard

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/traces` | evaluation:read / task:read |
| GET | `/api/v1/traces/{id}` | evaluation:read |
| POST | `/api/v1/traces/{id}/judge` | evaluation:submit |
| POST | `/api/v1/traces/{id}/review` | evaluation:approve |
| GET | `/api/v1/reports/{task_id}` | evaluation:read |
| GET | `/api/v1/dashboard` | task:read |
| GET | `/api/v1/dashboard/stats` | task:read |
| GET | `/api/v1/dashboard/overview` | task:read |
| GET | `/api/v1/diagnosis` | evaluation:read |
| GET | `/api/v1/diagnosis/{task_id}` | evaluation:read |
| GET | `/api/v1/diagnosis/trace/{trace_id}` | evaluation:read |

---

## 7. Logs / Observability / Audit

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/logs` | task:read / audit |
| GET | `/api/v1/logs/statistics` | task:read |
| GET | `/api/v1/observability/kpis` | task:read |
| GET | `/api/v1/observability/slow-tasks` | task:read |
| GET | `/api/v1/observability/error-topology` | task:read |
| GET | `/api/v1/audit` | audit:read |

---

## 8. Billing

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/billing/plans` | Plan catalog |
| GET | `/api/v1/billing/quota` | Current quota |
| GET | `/api/v1/billing/usage` | Usage records |
| POST | `/api/v1/billing/subscribe` | Subscribe |
| POST | `/api/v1/billing/checkout` | Stripe-compatible checkout (mock default) |
| POST | `/api/v1/billing/checkout/mock-confirm` | Mock payment confirm |
| POST | `/api/v1/billing/webhook/stripe` | **Public** (signature) |
| GET | `/api/v1/billing/invoices` | Invoices |
| POST | `/api/v1/billing/invoices/draft` | Draft invoice |
| POST | `/api/v1/billing/quota/rollover` | Period rollover |

---

## 9. Experiments / A/B / Media / Plugins / Tools / Settings

| Area | Prefix | Notes |
|------|--------|-------|
| Experiments | `/api/v1/experiments` | CRUD + compare |
| A/B | `/api/v1/ab` | Online experiments |
| Media | `/api/v1/media` | Multimodal upload/eval |
| Plugins | `/api/v1/plugins` | Market + lifecycle |
| Tools | `/api/v1/tools` | Sandbox list/probe |
| Settings | `/api/v1/settings` | Public settings + actor |
| WebSocket | `/api/v1/ws/...` | Realtime activities |

Full request/response schemas: generate/regenerate OpenAPI:

```bash
cd backend
python -m scripts.export_openapi -o ../docs/openapi-v1.json
```

---

## 10. Breaking change policy

**Forbidden without major version bump:**

- Remove or rename path/method  
- Remove required request field  
- Change field type incompatibly  
- Tighten auth on previously public business routes without migration note  

**Allowed:**

- New optional fields  
- New endpoints under `/api/v1`  
- New error codes with same HTTP class  

CI: `test_api_contract.py` loads frozen path set and compares to live OpenAPI.

---

*Freeze date: 2026-07-19 — AgentFlow-Eval v1 API*
