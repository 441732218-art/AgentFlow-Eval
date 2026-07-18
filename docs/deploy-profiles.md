# 部署形态（Deploy Profiles）

AgentFlow-Eval 通过 **Ports & Adapters** 支持三级交付，**不改业务流水线**：

| Profile | 适用 | DB | 队列 | 缓存 | 事件 | 计费 |
|---------|------|-----|------|------|------|------|
| **lite** | 个人演示 / 极简 | SQLite | eager（同进程） | 内存 L1 | 进程内 | 关 |
| **private** | 中小企业私有化 | Postgres | Celery | L1+L2 Redis | Redis | 可选 |
| **saas** | 云端订阅 | Postgres | Celery | L1+L2 Redis | Redis | 开（逐步） |

## 配置

```env
# auto | lite | private | saas
DEPLOY_PROFILE=auto

# 覆盖队列：celery | eager | memory（空=按 profile 默认）
TASK_QUEUE_BACKEND=

BILLING_ENABLED=false
CELERY_TASK_ALWAYS_EAGER=true   # 与 lite / 本地开发配合
DATABASE_URL=sqlite+aiosqlite:///./agentflow_eval.db
```

`DEPLOY_PROFILE=auto`：若 `sqlite` + `CELERY_TASK_ALWAYS_EAGER` → 视为 **lite**。

## 极简启动（零 Redis / 零 Celery Worker）

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-lite.ps1
```

### 手动

```bash
cd backend
# .env 建议：
# DEPLOY_PROFILE=lite
# CELERY_TASK_ALWAYS_EAGER=true
# DATABASE_URL=sqlite+aiosqlite:///./agentflow_eval.db
# AUTH_ENABLED=false
uvicorn app.main:app --reload --port 8000
```

另开终端：

```bash
cd frontend
npm run dev
```

健康检查：`GET /health/ready` → `deploy.profile=lite`，`redis=skipped`。

## 代码入口

| 能力 | 路径 |
|------|------|
| 装配 | `app/core/profiles/` |
| 队列 Port | `app/core/ports/task_queue.py` |
| Celery/Eager/Memory | `app/core/adapters/queue/` |
| 执行任务 | `POST /api/v1/tasks/{id}/execute` → `get_task_queue().enqueue(...)` |
| 身份/权限 | `GET /api/v1/me` |

## 私有化 / SaaS

沿用现有 `docker-compose.yml`（Postgres + Redis + Celery + backend + frontend）：

```env
DEPLOY_PROFILE=private
CELERY_TASK_ALWAYS_EAGER=false
TASK_QUEUE_BACKEND=celery
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://redis:6379/0
```
