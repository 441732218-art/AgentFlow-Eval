# API Reference — AgentFlow-Eval v1

**Base path:** `/api/v1`  
**Frozen contract:** [docs/api-contract.md](./docs/api-contract.md)  
**Machine schema:** [docs/openapi-v1.json](./docs/openapi-v1.json)

---

## Authentication

| Header | Description |
|--------|-------------|
| `X-API-Key: <secret>` | Preferred |
| `Authorization: Bearer <secret>` | Equivalent |
| `X-Tenant-ID: <uuid\|slug>` | When `MULTI_TENANT_ENABLED=true` |

Public (no key): `/health*`, `/metrics`, `/api/v1/billing/webhook*`.

---

## Core groups

| Group | Prefix | Highlights |
|-------|--------|------------|
| Me | `/me` | actor, role, permissions, tenant |
| Tenants | `/tenants` | enterprise orgs + members |
| Tasks | `/tasks` | create, execute, suites, archive |
| Traces | `/traces` | list, judge, human review |
| Dashboard | `/dashboard` | cockpit overview / stats |
| Diagnosis | `/diagnosis` | failure analysis |
| Logs | `/logs` | AOLS events + statistics |
| Billing | `/billing` | plans, plan, quota, usage, checkout, webhook |
| Benchmarks | `/benchmarks` | suites, import, run, leaderboard |
| Experiments / AB | `/experiments`, `/ab` | offline compare + online AB |
| Media | `/media` | multimodal |
| Plugins | `/plugins` | market + lifecycle |
| Audit | `/audit` | security audit trail |
| Observability | `/observability` | KPIs, slow tasks |
| Settings | `/settings` | public config + actor |

---

## Error envelope

```json
{
  "error": {
    "code": 429,
    "message": "Task quota exceeded...",
    "detail": { "code": "QUOTA_EXCEEDED", "metric": "task" },
    "timestamp": "..."
  },
  "request_id": "..."
}
```

| HTTP | Use |
|------|-----|
| 401 | Missing/invalid API key |
| 403 | RBAC / tenant membership |
| 404 | Missing or cross-tenant hidden |
| 429 | Rate limit or **QUOTA_EXCEEDED** |

---

## Export / compatibility

```bash
cd backend
python scripts/export_openapi.py -o ../docs/openapi-v1.json
python scripts/export_openapi.py --check ../docs/openapi-v1.json
```

Interactive docs (dev): `http://127.0.0.1:8000/docs`

---

## Permissions (enterprise)

See [docs/rbac-enterprise.md](./docs/rbac-enterprise.md).

Notable: `tenant:*`, `billing:*`, `benchmark:*` plus classic `task:*` / `evaluation:*`.
