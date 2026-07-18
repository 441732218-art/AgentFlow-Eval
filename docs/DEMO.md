# AgentFlow-Eval 演示剧本（P0）

**目标**：干净环境 15 分钟内跑通  
Lite 个人演示 **或** Docker Private 全栈演示。

---

## 路径 A：Lite（零 Redis / 零 Celery Worker）

```powershell
# 1) 启动
powershell -ExecutionPolicy Bypass -File scripts\start-lite.ps1

# 2) 校验
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 -BaseUrl http://127.0.0.1:8000

# 3) 演示剧本（API）
powershell -ExecutionPolicy Bypass -File scripts\demo-playbook.ps1 -BaseUrl http://127.0.0.1:8000
```

| 地址 | 说明 |
|------|------|
| http://127.0.0.1:5173 | 前端 Vite |
| http://127.0.0.1:8000/docs | OpenAPI |
| http://127.0.0.1:8000/health/ready | 就绪探针（应 `ready`，redis=skipped） |

---

## 路径 B：Docker Private（Postgres + Redis + Celery）

```powershell
# 1) 一键（含 alembic upgrade head + seed）
powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1 -Rebuild

# 2) 校验
powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1

# 3) 演示
powershell -ExecutionPolicy Bypass -File scripts\demo-playbook.ps1
```

| 地址 | 说明 |
|------|------|
| http://localhost/ | 前端 Nginx |
| http://localhost:8000/docs | API |
| http://localhost:5555 | Flower |

迁移由 compose 服务 `migrate` 执行（`alembic upgrade head`，含 **010 计费 / 011 慢任务**）。

---

## 剧本步骤（demo-playbook.ps1 自动跑）

| # | 步骤 | 期望 |
|---|------|------|
| 1 | `/health/ready` | `ready` |
| 2 | `/api/v1/me` | 有 role / permissions |
| 3 | 创建任务 | 201 + task id |
| 4 | 上传用例 | 可选 |
| 5 | execute | queued + job id |
| 6 | Checkout Pro (mock) | plan_code=pro |
| 7 | 装 `echo_tool` + `premium_length_judge` | 付费插件在 pro 后成功 |
| 8 | KPI | 返回 kpis 对象 |

---

## UI 手点路径（录屏友好）

1. **总览** `/` — 配额条 + KPI + 慢任务  
2. **任务** — 创建 / 执行  
3. **用量计费** `/billing` — 点 Pro「结账订阅」（mock 秒激活）  
4. **插件市场** `/plugins` — 安装免费 + 付费 mock  
5. **设置** — 主题 / API Key（若开启 AUTH）

---

## 生产前 5 分钟

```powershell
cd backend
# 使用生产 env 文件
$env:ENV="prod"
python -m app.cli.check_prod --force-prod
```

详见 [production-checklist.md](./production-checklist.md)。
