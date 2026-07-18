# 生产上线检查清单（P0）

> 增量交付清单，不推翻现有架构。勾选后再对公网放量。

## 1. 配置（必须）

| 项 | 要求 | 检查 |
|----|------|------|
| `ENV` | `prod` | `python -m app.cli.check_prod --force-prod` |
| `DEBUG` | `false` | 同上 |
| `SECRET_KEY` | ≥16 随机，非默认 | 同上 |
| `DATABASE_URL` | Postgres（非 sqlite） | compose / 托管库 |
| `REDIS_URL` | 可达 | `/health/ready` services.redis=ok |
| `CORS_ORIGINS` | 仅前端域名 | 配置审查 |
| `AUTH_ENABLED` | 建议 `true` | 配 `API_KEYS` |
| `DEPLOY_PROFILE` | `private` 或 `saas` | 非 lite 公网 |

```bash
cd backend
python -m app.cli.check_prod --force-prod --strict
```

## 2. 数据库迁移

```bash
# Docker
docker compose --env-file .env.docker run --rm migrate
# 或
docker compose exec backend alembic upgrade head

# 本地
alembic upgrade head
```

确认 head 包含：

- `009_ab_tests`
- `010_billing`
- `011_slow_task_events`

## 3. 健康探针（编排）

| 探针 | 路径 | 期望 |
|------|------|------|
| Liveness | `GET /health/live` | 200 `alive` |
| Readiness | `GET /health/ready` | 200 `ready`（DB ok；非 eager 时 Redis ok） |
| 兼容 | `GET /health` | healthy / degraded |

Docker Compose 已使用 `/health/ready`。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 -BaseUrl https://api.example.com
```

## 4. 可观测

- [ ] Prometheus scrape `GET /metrics`
- [ ] 导入 [grafana-agentflow.json](./grafana-agentflow.json)
- [ ] 日志 `LOG_FORMAT=json`，可按 `request_id` / TraceID 检索

## 5. 安全

- [ ] 关闭公网 `/docs`（`ENV=prod` 已默认关闭 Swagger）
- [ ] `AUTH_ENABLED=true` + 强 `API_KEYS`
- [ ] 限制 `ADMIN_ACTORS` / RBAC
- [ ] 插件：`PLUGIN_STRICT_ALLOWLIST=true` + 明确 `PLUGIN_MODULES`（勿扫公网目录）
- [ ] Stripe：公网仅暴露 webhook；`STRIPE_MODE=live` 时配密钥

## 6. SaaS 开关（可选）

```env
DEPLOY_PROFILE=saas
BILLING_ENABLED=true
STRIPE_MODE=mock   # 上线收款再改 live
```

## 7. 回滚

1. `docker compose down` / 回滚镜像 tag  
2. DB 不自动 downgrade（默认）；必要时 `alembic downgrade -1`（评估后）  
3. 保留 `postgres_data` 卷  

## 8. 一键入口汇总

| 动作 | 命令 |
|------|------|
| Lite 启动 | `scripts/start-lite.ps1` |
| Private Docker | `scripts/docker-up.ps1` |
| 部署后校验 | `scripts/post-deploy-verify.ps1` |
| 演示剧本 | `scripts/demo-playbook.ps1` |
| 配置校验 | `cd backend && make check-prod` |
