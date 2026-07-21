# Deployment Guide — AgentFlow-Eval v1.0

Enterprise Agent Evaluation Platform. Supports **lite**, **private**, and **saas** profiles.

---

## 1. Choose a profile

| Profile | When | Compose / start |
|---------|------|-----------------|
| **lite** | Demo, laptop, soft-copyright screenshots | `scripts/start-lite.ps1` or `docker compose -f docker-compose.lite.yml` |
| **private** | On-prem / VPC | `backend/docker-compose.yml` or `docker-compose.prod.yml` |
| **saas** | Multi-tenant + billing | private stack + `.env.saas.example` flags |

Env templates:

- [`.env.lite.example`](./.env.lite.example)
- [`.env.private.example`](./.env.private.example)
- [`.env.saas.example`](./.env.saas.example)
- [`backend/.env.example`](./backend/.env.example)
- [`backend/.env.docker.example`](./backend/.env.docker.example)

---

## 2. Docker one-shot (private)

```bash
# Generate secrets (Windows)
powershell -ExecutionPolicy Bypass -File scripts/generate-deploy-env.ps1

# Or copy
cp .env.private.example backend/.env.docker
# edit SECRET_KEY, POSTGRES_PASSWORD, API_KEYS, OPENAI_API_KEY

cd backend
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up -d
# migrate runs via compose service; or:
# docker compose --env-file .env.docker run --rm migrate

# optional seed
docker exec -e PYTHONPATH=/app agentflow-backend python -m app.core.seed --force
```

**Endpoints**

| URL | Purpose |
|-----|---------|
| http://127.0.0.1/ | UI (nginx → API) |
| http://127.0.0.1:8000/health/ready | API readiness |
| http://127.0.0.1:8000/docs | OpenAPI (protect in prod) |

Production registry images:

```bash
export BACKEND_IMAGE=ghcr.io/ORG/AgentFlow-Eval-backend:v1.0.0
export FRONTEND_IMAGE=ghcr.io/ORG/AgentFlow-Eval-frontend:v1.0.0
cd backend
docker compose -f docker-compose.prod.yml --env-file .env.docker up -d
```

Optional observability:

```bash
docker compose -f docker-compose.prod.yml --profile obs up -d
# Prometheus :9090  Grafana :3000
```

---

## 3. Images

| Dockerfile | Notes |
|------------|-------|
| `backend/Dockerfile` / `Dockerfile.backend` | Multi-stage, **non-root** uid 10001 |
| `frontend/Dockerfile` | Multi-stage nginx :80 |
| `frontend/Dockerfile.frontend` | Non-root nginx :8080 |

```bash
docker build -f backend/Dockerfile.backend -t agentflow-backend:local backend
docker build -f frontend/Dockerfile -t agentflow-frontend:local frontend
```

---

## 4. Auth & multi-tenant

```env
AUTH_ENABLED=true
API_KEYS=af-xxxx:admin:system_admin
MULTI_TENANT_ENABLED=true   # SaaS
```

UI: open `http://127.0.0.1/` — private stack may auto-bootstrap API key via nginx/runtime-config.  
API: header `X-API-Key` and optional `X-Tenant-ID`.

---

## 5. Migrations

```bash
cd backend
alembic upgrade head
# includes 013 tenants, 014 billing limits, 015 benchmarks
```

---

## 6. CI/CD

| Workflow | Trigger |
|----------|---------|
| `.github/workflows/test.yml` | PR/push — ruff, bandit (medium+), pytest cov≥40% |
| `.github/workflows/docker-build.yml` | **唯一**镜像流水线：PR 仅构建；main/tags 构建+推送 GHCR+Trivy |
| `.github/workflows/release.yml` | tags `v1.*` — 测试门禁 + GitHub Release Notes（**不再**重复构建镜像） |
| `.github/workflows/build-windows.yml` / `desktop-macos.yml` | 桌面安装包 → Release Assets |
| `.github/workflows/deploy.yml` | manual SSH deploy (secrets) |

> 已删除冗余的 `build.yml`，避免与 `docker-build.yml` 双推镜像导致分钟浪费与偶发失败。

---

## 7. Verify

```powershell
powershell -File scripts/post-deploy-verify.ps1
curl -f http://127.0.0.1:8000/health/ready
curl -f http://127.0.0.1/health
```

Production checklist: [docs/production-checklist.md](./docs/production-checklist.md)

---

## 8. Security baseline (prod)

- Strong `SECRET_KEY`, `API_KEYS`, DB password  
- `AUTH_ENABLED=true`, tight `CORS_ORIGINS`  
- `PLUGIN_STRICT_MODE=true`  
- Prefer non-root backend image; network-isolate Postgres/Redis  
- See [SECURITY.md](./SECURITY.md) and [docs/security-audit-report.md](./docs/security-audit-report.md)
