# AgentFlow Intelligence — Offline Delivery Package

| Field | Value |
|-------|-------|
| Copyright | 李凯昕 |
| Shape | Docker private stack (Postgres + Redis + API + Celery + Frontend) |

## 1. Load images

```powershell
docker load -i images\agentflow-images.tar
docker images | findstr agentflow
```

Expected tags:

- `agentflow-backend:local`
- `agentflow-frontend:local`
- `postgres:16-alpine`
- `redis:7-alpine`

## 2. Configure secrets

```powershell
copy config\.env.docker.example config\.env.docker
# Edit config\.env.docker:
#   SECRET_KEY / POSTGRES_PASSWORD / OPENAI_API_KEY
#   AUTH_ENABLED=true
#   API_KEYS=your-random-secret:admin:admin
```

## 3. Start

```powershell
cd config
docker compose --env-file .env.docker -f docker-compose.yml up -d
# Production (no host ports for DB/Redis):
# docker compose --env-file .env.docker -f docker-compose.prod.yml up -d
```

## 4. Access

| URL | Notes |
|-----|-------|
| http://127.0.0.1/ | UI + `/api` reverse proxy |
| http://127.0.0.1:8000/health/ready | API readiness |
| http://127.0.0.1:8000/api/v1/me | Requires `X-API-Key` header |

Put the secret part of `API_KEYS` into Frontend **Settings**.

## 5. Post-deploy verify

```powershell
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 -BaseUrl http://127.0.0.1:8000 -ApiKey "your-secret"
```

## 6. Security checklist

- [ ] `AUTH_ENABLED=true` with strong `API_KEYS`
- [ ] `SECRET_KEY` and DB password are non-default
- [ ] Postgres/Redis not exposed publicly (`docker-compose.prod.yml` has no host ports)
- [ ] `ENV=prod` disables `/docs`
- [ ] Flower only via compose profile `ops`

## 7. Rollback

```powershell
docker compose --env-file .env.docker down
# wipe volumes: docker compose down -v
```
