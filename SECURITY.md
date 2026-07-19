# Security Policy — AgentFlow-Eval

## Supported versions

| Version | Status |
|---------|--------|
| **1.0.x** | Active security fixes |
| 0.1.x / earlier | Best effort only |

## Reporting a vulnerability

**Do not** open a public GitHub issue for exploitable vulnerabilities.

Prefer:

1. GitHub **Security → Report a vulnerability** (if enabled)  
2. Private contact with the repository owner  

Include: impact, reproduction steps, whether an exploit is known, and contact info.

## Production hardening checklist

| Control | Recommendation |
|---------|----------------|
| Auth | `AUTH_ENABLED=true` + strong random `API_KEYS` |
| Secrets | Never commit `.env` / `.env.docker`; rotate on leak |
| CORS | Explicit production origins only |
| Tenancy | `MULTI_TENANT_ENABLED=true` for SaaS |
| Plugins | `PLUGIN_STRICT_MODE=true`; optional `PLUGIN_SIGNATURE_CHECK=true` |
| Containers | Prefer `Dockerfile.backend` non-root; `no-new-privileges` |
| Network | Do not publish Postgres/Redis publicly |
| TLS | Terminate TLS at reverse proxy / load balancer |
| Rate limit | `RATE_LIMIT_ENABLED=true` |
| Docs | Restrict `/docs` and `/redoc` on public internet |

## Built-in protections

- Constant-time API key comparison  
- RBAC permission matrix (enterprise roles)  
- Actor + tenant isolation (404 on cross-tenant)  
- Security response headers middleware  
- Structured audit logs (`/api/v1/audit`)  
- Billing quota gate → **429 QUOTA_EXCEEDED**  
- Settings guard for weak prod `SECRET_KEY` / `DEBUG`  

## Tooling

```bash
cd backend
bandit -r app/ -ll
pip-audit -r requirements.txt
# after image build:
trivy image agentflow-backend:local
```

CI: `.github/workflows/test.yml`, `docker-build.yml` (Trivy).

Full review: [docs/security-audit-report.md](./docs/security-audit-report.md).

## If secrets leak

1. Rotate provider API keys (OpenAI, Stripe, …)  
2. Rotate `SECRET_KEY`, `API_KEYS`, DB passwords  
3. Purge git history if credentials were committed  
4. Review audit logs for abuse  
