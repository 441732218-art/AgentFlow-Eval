# Security Audit Report â€?AgentFlow-Eval v1.0

| Field | Value |
|-------|-------|
| Date | 2026-07-19 |
| Scope | API, auth, multi-tenant, plugins, Docker, CI |
| Method | Static review + unit tests + tooling recommendations |

---

## 1. OWASP Top 10 mapping

| Risk | Status | Notes |
|------|--------|-------|
| A01 Broken Access Control | **Mitigated** | API key + RBAC + tenant_id / created_by isolation; IDOR hidden as 404 |
| A02 Cryptographic Failures | **Partial** | HMAC API key compare; TLS depends on edge proxy; secrets via env |
| A03 Injection | **Mitigated** | SQLAlchemy ORM; parameterized queries |
| A04 Insecure Design | **Mitigated** | Deploy profiles; billing/tenant flags default safe for lite |
| A05 Security Misconfiguration | **Hardened** | Production settings_guard; security headers middleware |
| A06 Vulnerable Components | **Process** | CI: bandit, pip-audit (advisory), Trivy on images |
| A07 Auth Failures | **Mitigated** | AUTH_ENABLED + constant-time key compare; public path allowlist |
| A08 Data Integrity | **Partial** | Plugin HMAC optional (`PLUGIN_SIGNATURE_CHECK`) |
| A09 Logging Failures | **Mitigated** | AOLS + audit_logs; secrets redaction |
| A10 SSRF | **Partial** | HttpAgentRunner user-controlled URLs â€?restrict network in prod |

---

## 2. Critical / High findings & fixes

| ID | Severity | Finding | Remediation (v1.0) |
|----|----------|---------|---------------------|
| H1 | High | Containers ran as root | Backend multi-stage + `USER agentflow` (uid 10001); compose `user: 10001:10001` |
| H2 | High | Plugin dynamic load unrestricted | `PLUGIN_STRICT_MODE` / allowlist; optional `PLUGIN_SIGNATURE_CHECK` |
| H3 | Medium | Default AUTH off in examples | Private/SaaS env examples set `AUTH_ENABLED=true` |
| H4 | Medium | OpenAPI /docs in prod | Document disable or protect behind network policy |
| H5 | Medium | CORS wide open if mis-set | Env templates use explicit origins |
| M1 | Medium | Rate limit optional dep | `RATE_LIMIT_ENABLED=true` in private/saas examples |
| M2 | Low | CSRF | API-key header model (no cookie session) |
| M3 | Low | Frontend entrypoint root | Documented; `Dockerfile.frontend` non-root:8080 available |

---

## 3. Plugin security controls

| Control | Env | Default |
|---------|-----|---------|
| Strict mode | `PLUGIN_STRICT_MODE` / `PLUGIN_STRICT_ALLOWLIST` | false (lite) / true (prod templates) |
| Allowlist | `PLUGIN_ALLOWLIST` | empty |
| Signature | `PLUGIN_SIGNATURE_CHECK` + `PLUGIN_SIGNING_SECRET` + `PLUGIN_SIGNATURES` | false |

---

## 4. Recommended scan commands

```bash
# Bandit
cd backend && bandit -c .bandit -r app/ -ll -i -f txt

# pip-audit
pip-audit -r requirements.txt

# Trivy (after docker build)
trivy image agentflow-backend:local
trivy image agentflow-frontend:local

# Semgrep (optional local)
semgrep --config=p/python app/
```

CI: `.github/workflows/test.yml` (bandit high), `docker.yml` (Trivy).

---

## 5. Residual risk acceptance

- Full 80% test coverage is a **roadmap target**; CI gate currently **40%**.
- Live Stripe and SSO not required for private v1.0.
- Operator must supply strong `SECRET_KEY` / `API_KEYS` / DB passwords before public exposure.

**Audit verdict:** Critical container-root and plugin load paths addressed for v1.0 private/saas templates; suitable for **controlled enterprise release** with AUTH on and network isolation.
