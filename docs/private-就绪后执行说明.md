# Private 部署就绪后执行说明

| 属性 | 内容 |
|------|------|
| **适用场景** | 已看到 `GET /health/ready` 返回 `status: ready`，且 `deploy.profile = private` |
| **产品** | AgentFlow Intelligence（仓库 AgentFlow-Eval） |
| **文档性质** | 操作说明 + 落地 checklist（非设计文档） |
| **对照截图** | 就绪 JSON：`database=ok`、`redis=ok`、`task_queue=celery`、`eager=false` |

---

## 1. 你现在处在什么状态？

下表对应就绪接口返回的字段（与浏览器 / Swagger 中 `/health/ready` 一致）：

```json
{
  "status": "ready",
  "app": "AgentFlow Intelligence",
  "version": "0.1.0",
  "services": {
    "database": "ok",
    "redis": "ok"
  },
  "celery_eager": false,
  "deploy": {
    "profile": "private",
    "task_queue": "celery",
    "cache": "redis_l2",
    "event_bus": "redis",
    "metering": "noop",
    "eager": false,
    "applied": true
  }
}
```

### 1.1 字段释义

| 字段 | 你的值 | 含义 |
|------|--------|------|
| `status` | **ready** | 可以接业务流量（DB 通；非 eager 时 Redis 通） |
| `app` | AgentFlow Intelligence | 应用显示名 |
| `version` | **0.1.0** | **运行时健康接口版本号**（见 §6 版本说明） |
| `services.database` | **ok** | Postgres/SQLite 探针成功 |
| `services.redis` | **ok** | Redis 可达（private 必需） |
| `celery_eager` | **false** | 任务**不在 API 进程内**同步跑，需 Celery Worker |
| `deploy.profile` | **private** | 私有化剖面（非 lite / 非 saas） |
| `deploy.task_queue` | **celery** | 异步评测走 Celery 队列 |
| `deploy.cache` | **redis_l2** | L1 内存 + L2 Redis 缓存 |
| `deploy.event_bus` | **redis** | 事件总线走 Redis |
| `deploy.metering` | **noop** | 计量端口未接真实计费计量（私有化默认可接受） |
| `deploy.eager` | **false** | 与 `celery_eager` 一致：全异步栈 |
| `deploy.applied` | **true** | 部署剖面已成功装配到运行时 |

### 1.2 一句话结论

> **Private 全栈已就绪**：数据库 + Redis 健康，任务将走 **Celery 异步**，适合「企业内网 / 私有化演示与交付」路径。  
> 这 **不等于** 已完成鉴权加固、演示数据、前端联调或客户验收。

| 已确认 | 尚未由本 JSON 证明 |
|--------|-------------------|
| API 进程可服务 | 前端页面可访问 |
| DB / Redis 通 | Celery Worker 进程在跑且消费队列 |
| profile=private 已应用 | `AUTH`、迁移 head、seed、业务 API 全通 |

---

## 2. 就绪后建议立即执行的 6 步

按顺序执行；任一步失败先停，再往下做业务演示。

### 步骤 0 — 确认你在查哪个地址

| 启动方式 | 常见 API 基址 | 前端 |
|----------|---------------|------|
| Docker Private（compose） | `http://127.0.0.1:8000` 或 `http://localhost:8000` | `http://localhost/`（Nginx） |
| 本机仅后端 | `http://127.0.0.1:8000` | `http://127.0.0.1:5173`（Vite） |

就绪探针（无需 API Key）：

```text
GET {BaseUrl}/health/ready
```

浏览器打开示例：

```text
http://127.0.0.1:8000/health/ready
```

### 步骤 1 — 一键部署后校验（推荐）

在项目根目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 -BaseUrl http://127.0.0.1:8000
```

期望：`/health/live` alive、`/health/ready` ready，并打印与截图类似的 `deploy` / `services`。

若开启了鉴权，可带 Key：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 `
  -BaseUrl http://127.0.0.1:8000 `
  -ApiKey "你的密钥"
```

或设置环境变量 `AGENTFLOW_API_KEY`（脚本也会尝试从 `backend/.env.docker` 的 `API_KEYS` 取第一个 secret）。

### 步骤 2 — 确认 Celery Worker 在跑

`celery_eager=false` 时，**没有 Worker 则任务会一直排队**。

Docker 栈：

```powershell
cd backend
docker compose --env-file .env.docker ps
# 应看到 backend / worker（或 celery）/ redis / postgres / frontend 等 healthy 或 running
```

日志侧可看 worker 是否消费：

```powershell
docker compose --env-file .env.docker logs -f worker
# 服务名以你 compose 实际名为准，可能是 celery / worker
```

### 步骤 3 — 数据库迁移到 head

Private 交付应跑到当前仓库最新迁移（含租户 / 计费 / Benchmark 等）：

```powershell
cd backend
docker compose --env-file .env.docker run --rm migrate
# 或
docker compose --env-file .env.docker exec backend alembic upgrade head
```

本地非 Docker：

```powershell
cd backend
alembic upgrade head
```

当前仓库迁移序号至 **015_benchmarks**（以 `backend/alembic/versions/` 为准）。

### 步骤 4 — 写入演示数据（驾驶舱 / 诊断 / 监控有数）

```powershell
cd backend
docker compose --env-file .env.docker exec backend python -m app.core.seed --force
# 本地：
# python -m app.core.seed --force
```

期望输出大致包含：演示任务、多条 Trace（含失败样例）、AgentLogs 等。

### 步骤 5 — API 演示剧本（可选自动化）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo-playbook.ps1 -BaseUrl http://127.0.0.1:8000
```

覆盖：ready → me → 建任务 → 执行 →（mock）计费/插件等。详见 [DEMO.md](./DEMO.md)。

### 步骤 6 — UI 手点验收（私有化演示）

| 顺序 | 页面 | 验收点 |
|------|------|--------|
| 1 | 前端首页 / 驾驶舱 `/dashboard` | 有任务/AOLS 类指标，非全空 |
| 2 | 任务列表 → 详情 → 执行 | 状态进入 queued/running/completed（Worker 正常时） |
| 3 | Trace Explorer `/traces` | 能看到步骤 / DAG |
| 4 | 故障诊断 `/diagnosis` | seed 后可选到失败样例 |
| 5 | 监控 `/monitoring` | 日志列表有事件 |
| 6 | 设置 | 若 `AUTH_ENABLED=true`，配置 `X-API-Key` |

生产勾选清单见 [production-checklist.md](./production-checklist.md)。

---

## 3. 按目标客户的「还差什么 / 先做什么」

结合你当前 **private + ready** 状态：

### 3.1 只做内网私有化交付（推荐主路径）

| 优先级 | 事项 | 做法 |
|--------|------|------|
| P0 | 打开鉴权 | `AUTH_ENABLED=true`，配置强 `API_KEYS` / `SECRET_KEY` |
| P0 | 生产配置门禁 | `cd backend; python -m app.cli.check_prod --force-prod --strict` |
| P0 | 迁移 + seed + Worker | 见 §2 步骤 2–4 |
| P0 | CORS / 域名 | `CORS_ORIGINS` 仅前端域名；DB/Redis 不暴露公网 |
| P1 | 演示剧本与操作手册 | [DEMO.md](./DEMO.md)、[用户操作手册.md](./用户操作手册.md) |
| P1 | 可观测 | Prometheus 刮 `/metrics`，可选 Grafana 导入 `grafana-agentflow.json` |
| P2 | 插件安全 | 生产 `PLUGIN_STRICT_ALLOWLIST=true`，按需 `PLUGIN_SIGNATURE_CHECK` |

**本路径结论**：就绪 JSON 已通过 → 补鉴权与演示数据后，即可作为 **私有化试用 / PoC 交付**。

### 3.2 受控 SaaS 试点（同一套代码，换剖面）

在 private 跑通后：

```env
DEPLOY_PROFILE=saas
BILLING_ENABLED=true
STRIPE_MODE=mock   # 真收款前不要上 live
```

| 优先级 | 事项 | 说明 |
|--------|------|------|
| P0 | 多租户 + `X-Tenant-ID` | 代码已有；验收跨租户不可见 |
| P0 | 企业 RBAC | system_admin / tenant_admin / member / viewer |
| P1 | 配额 429 | 超额返回 `QUOTA_EXCEEDED` |
| P1 | Stripe live | 1.x 路线，非当前 must |
| P2 | SSO/OIDC | 未做，试点可用 API Key |

**本路径结论**：数据面可试点；**勿对外承诺**完整计费与 SSO。

### 3.3 开源公开发布 / 对齐 origin

| 事项 | 说明 |
|------|------|
| 版本叙事 | 文档写 v1.0.0，健康接口仍 `0.1.0`（见 §6） |
| Git | 本地 main 可能领先 origin，发版前统一 tag 与 CHANGELOG |
| LICENSE / 软著 | 权利人、版本号与公开材料一致后再 push |

---

## 4. 常见异常对照

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `status: not_ready`，database error | DB 未起 / `DATABASE_URL` 错 | 查 compose、`.env.docker`、迁移 |
| `redis: unavailable` | Redis 未起或 URL 错 | private 必须修 Redis；lite 才会 skipped |
| ready 但任务一直 queued | Worker 未启动 / 队列名不一致 | `docker compose ps` + worker 日志 |
| 401 / 403 | `AUTH_ENABLED=true` 未带 Key | 请求头 `X-API-Key` |
| 驾驶舱全空 | 未 seed、无真实任务 | `python -m app.core.seed --force` |
| 前端能开但 API 失败 | 反代 / CORS / 端口 | 查 Nginx `localhost` 与 `8000` 是否一致 |

---

## 5. 与 Lite 的差异（避免误判）

| 项 | 你当前（Private） | Lite |
|----|-------------------|------|
| `deploy.profile` | private | lite |
| Redis | **ok（必需）** | skipped |
| 队列 | celery + Worker | eager 同进程 |
| 适用 | 私有化 / 接近生产 | 个人演示零中间件 |

**不要**在 private 就绪后改回 eager 却仍声称「生产栈」，除非明确降级为演示。

---

## 6. 版本号说明（避免对外口径打架）

| 位置 | 常见值 | 说明 |
|------|--------|------|
| `GET /health/ready` → `version` | **0.1.0** | 代码常量 `APP_VERSION`（`backend/app/main.py`） |
| CHANGELOG / FINAL_RELEASE_REPORT | **1.0.0** | 产品发布叙事 |
| 软著材料 | V1.0.0 / V2.0.0 | 申请用版本，与运行时可能不同步 |

**对外演示建议**：

- 技术截图：如实说明「运行时 health 版本字段为 0.1.0」。
- 产品介绍：写「AgentFlow Intelligence 私有化交付基线（文档版本 1.0.x）」并指向 `FINAL_RELEASE_REPORT.md`。
- 若需统一：将 `APP_VERSION` / FastAPI `version=` 改为 `1.0.0` 后再截图归档。

---

## 7. 推荐命令速查

```powershell
# 就绪
Invoke-RestMethod http://127.0.0.1:8000/health/ready

# 部署校验
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1

# Docker 拉起（若尚未启动）
powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1

# 演示 seed
cd backend; docker compose --env-file .env.docker exec backend python -m app.core.seed --force

# API 剧本
powershell -ExecutionPolicy Bypass -File scripts\demo-playbook.ps1

# 生产配置检查
cd backend; python -m app.cli.check_prod --force-prod --strict
```

---

## 8. 相关文档

| 文档 | 用途 |
|------|------|
| [DEMO.md](./DEMO.md) | 15 分钟演示剧本 |
| [deploy-profiles.md](./deploy-profiles.md) | lite / private / saas |
| [production-checklist.md](./production-checklist.md) | 上线勾选 |
| [跨端打包与安装交付.md](./跨端打包与安装交付.md) | 手机/电脑安装包、三大系统、自适应 UI |
| [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) | 部署总指南 |
| [落地执行报告-完整与可部署.md](./落地执行报告-完整与可部署.md) | 落地基线与债务 |
| [FINAL_RELEASE_REPORT.md](../FINAL_RELEASE_REPORT.md) | v1.0 发布结论 |

---

## 9. 本说明的验收定义（Definition of Done）

在截图所示 ready 基础上，完成下列即视为 **Private 可演示落地**：

- [x] `/health/ready` → `status=ready`，`profile=private`，DB/Redis ok  
- [ ] Celery Worker 运行中，执行任务可完成  
- [ ] `alembic` 已 upgrade head  
- [ ] seed 后驾驶舱 / 诊断 / 监控非空  
- [ ] 私有化环境 `AUTH_ENABLED=true` + 强密钥（对客演示前）  
- [ ] `post-deploy-verify.ps1` 全绿  

**当前截图完成项：第 1 项。** 按 §2 继续即可闭环。

---

*文档对应：Private 剖面就绪后的执行与落地说明 · AgentFlow Intelligence*
