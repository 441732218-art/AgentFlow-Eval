<p align="center">
  <img src="docs/brand/logo-dark.svg" alt="AgentFlow Intelligence" width="360"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <a href="https://github.com/441732218-art/AgentFlow-Eval/actions/workflows/ci.yml">
    <img src="https://github.com/441732218-art/AgentFlow-Eval/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
</p>

# AgentFlow Intelligence

企业级 **AI Agent Observability · Evaluation · Diagnosis** 平台（仓库名：AgentFlow-Eval）。

上传测试用例 → 异步执行 Agent → Trace DAG → LLM-as-Judge → 故障诊断 → Command Center 驾驶舱。

> **无需在线部署即可完整体验。** 推荐本地 Docker 或「Eager 模式」一键跑通。  
> 品牌资产见 [`docs/brand/`](docs/brand/) · UI 资源见 `frontend/public/assets/logo/`

---

## 核心特性

- **端到端评测流水线**：任务管理、CSV/JSON 用例导入、异步执行、取消/归档
- **ReAct Agent 执行器**：OpenAI 兼容接口 + 可扩展 `BaseAgentRunner`
- **工具沙箱**：天气/计算/航班/邮件等内置工具，可探测调试
- **链路可视化**：Trace 步骤存储 + ReactFlow DAG 展示
- **混合评分**：规则指标（工具准确率等）+ LLM-as-Judge + 人工复核改分
- **企业能力**：API Key 鉴权、租户隔离、审计日志、WebSocket 活动推送、限流
- **工程化**：Alembic 迁移、Celery + Redis、Docker Compose、CI（lint/test）

---

## 架构一览

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Ant Design + ReactFlow)           │
│  总览 / 任务 / 详情(DAG) / 报告 / 设置 / 审计                   │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST + WebSocket  /api/v1
┌───────────────────────────▼─────────────────────────────────┐
│  Backend (FastAPI)                                          │
│  tasks · traces · reports · tools · settings · audit · ws   │
└───────┬─────────────────────────────┬───────────────────────┘
        │                             │
   ┌────▼────┐                 ┌──────▼──────┐
   │ Celery  │                 │  PostgreSQL │
   │ Worker  │── Redis ──►     │  or SQLite  │
   └────┬────┘                 └─────────────┘
        │
   AgentRunner → Trace → JudgeEngine → MetricScore / Report
```

更完整的说明见 [docs/README.md](docs/README.md) 与 [docs/软件设计说明书.md](docs/软件设计说明书.md)。

---

## 跨端安装与打包（手机 + 电脑）

| 形态 | 命令 / 路径 | 说明 |
|------|-------------|------|
| **自适应 Web / PWA** | `cd frontend && npm run build:web` | 安装到手机主屏幕 / 电脑浏览器（Win·macOS·Linux） |
| **桌面安装包** | `scripts\build-release.ps1 -Targets web,desktop` | Electron：Windows exe / macOS dmg / Linux AppImage |
| **一键发行** | `scripts\build-release.ps1` | 产物在 `artifacts/release/` |
| **Docker 私有化** | `scripts\docker-up.ps1` | 服务端全栈；客户端用浏览器或 PWA/桌面包连接 |

详见 [docs/跨端打包与安装交付.md](docs/跨端打包与安装交付.md)。UI 已按手机 / 平板 / 桌面自适应（底栏 + 抽屉 + 安全区）。

---

## 快速开始（推荐）

| 形态 | 命令 | 依赖 |
|------|------|------|
| **Lite 极简** | `scripts\start-lite.ps1` | 仅 Python + Node（无 Redis/Celery） |
| **Eager 本地** | 方式 B | SQLite + 同进程任务 |
| **Private 全栈** | 方式 A Docker Compose | Postgres + Redis + Celery |

| 交付动作 | 命令 |
|----------|------|
| 部署后校验 | `scripts\post-deploy-verify.ps1` |
| 演示剧本 | `scripts\demo-playbook.ps1` |
| 生产检查清单 | [docs/production-checklist.md](docs/production-checklist.md) |
| 演示一页纸 | [docs/DEMO.md](docs/DEMO.md) |

详见 [docs/deploy-profiles.md](docs/deploy-profiles.md)。

### 方式 0：Lite 一键（个人演示 / 零中间件）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-lite.ps1
```

环境：`DEPLOY_PROFILE=lite`、`TASK_QUEUE_BACKEND=eager`、SQLite。健康检查会跳过 Redis。

### 方式 A：Docker 全栈（完整能力：Postgres + Redis + Celery）

**前置：** Docker Desktop / Docker Engine + Compose

```bash
# 1) 生成本地环境文件（Windows）
powershell -ExecutionPolicy Bypass -File scripts\generate-deploy-env.ps1

# 2) 编辑 backend/.env.docker ，填入 OPENAI_API_KEY

# 3) 启动
powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1
# 或
cd backend && docker compose --env-file .env.docker up -d --build
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost/ |
| API / Swagger | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| Flower（可选） | http://localhost:5555 |

写入演示数据：

```bash
cd backend
docker compose --env-file .env.docker exec backend python -m app.core.seed
```

### 方式 B：本地 Eager（最小依赖，无需 Redis）

**前置：** Python 3.11+、Node.js 18+

```bash
# 后端
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：OPENAI_API_KEY=...  且 CELERY_TASK_ALWAYS_EAGER=true
uvicorn app.main:app --reload --port 8000

# 另开终端：前端
cd frontend
npm install
cp .env.example .env.local   # 默认 VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm run dev
```

访问 http://localhost:5173  

Windows 也可：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1
```

种子数据：

```bash
cd backend
python -m app.core.seed
```

---

## 环境变量对照

| 文件 / 变量 | 用途 | 是否提交 Git |
|-------------|------|--------------|
| `backend/.env` | 本地 venv 开发（SQLite + Eager） | 否 |
| `backend/.env.example` | 上述模板 | 是 |
| `backend/.env.docker` | Docker Compose | 否 |
| `backend/.env.docker.example` | Docker 模板 | 是 |
| `deploy.env.example` | 云服务器 → `backend/.env` | 是 |
| `frontend/.env.local` | 本地 Vite `VITE_API_BASE_URL` | 否 |
| `frontend/.env.example` | 前端变量说明 | 是 |
| `VITE_API_BASE_URL` | 前端 API 根路径（须含 `/api/v1`） | 构建时注入 |

**生产注意：** `CELERY_TASK_ALWAYS_EAGER=false`，并启动 Redis + Celery Worker。

---

## 项目结构

```
AgentFlow-Eval/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/          # REST / WebSocket 路由
│   │   ├── core/
│   │   │   ├── agent_runner/    # Agent 执行
│   │   │   ├── judge_engine/    # 评分引擎
│   │   │   ├── celery_app/      # 异步任务
│   │   │   └── seed.py          # 演示数据
│   │   ├── models/ · schemas/ · utils/
│   ├── alembic/             # 数据库迁移
│   ├── tests/               # 单元 / E2E 测试
│   └── docker-compose.yml
├── frontend/                # React + TypeScript
│   └── src/
│       ├── api/             # HTTP 客户端（推荐）
│       ├── pages/ · components/ · stores/ · hooks/
├── docs/                    # 文档中心（见 docs/README.md）
├── scripts/                 # 启动 / 部署 / 环境生成脚本
├── LICENSE                  # MIT
├── CONTRIBUTING.md
├── CHANGELOG.md
└── SECURITY.md
```

---

## 主要 API

完整交互文档：启动后端后打开 **http://localhost:8000/docs**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/v1/tasks` | 任务列表 / 创建 |
| POST | `/api/v1/tasks/{id}/execute` | 执行评测 |
| POST | `/api/v1/tasks/{id}/test-suites/upload` | 上传 CSV/JSON 用例 |
| GET | `/api/v1/traces/{id}` | 执行轨迹详情 |
| POST | `/api/v1/traces/{id}/judge` | LLM 评分 |
| GET | `/api/v1/reports/{id}` | 评测报告 |
| GET | `/api/v1/audit` | 审计日志 |
| GET | `/api/v1/tools` | 沙箱工具列表 |

---

## 测试

```bash
# 后端
cd backend
pytest tests/unit/ -v
pytest tests/test_e2e.py -v
pytest tests/unit/ --cov=app --cov-report=term-missing

# 前端
cd frontend
npm test
# npm run test:e2e   # 需服务已启动或 Playwright webServer
```

CI：`.github/workflows/ci.yml`（push / PR 到 `main`）。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | 文档导航 |
| [docs/软件设计说明书.md](docs/软件设计说明书.md) | 架构与设计（软著材料） |
| [docs/用户操作手册.md](docs/用户操作手册.md) | 操作说明（软著材料） |
| [docs/功能模块清单.md](docs/功能模块清单.md) | 模块 ↔ 源码 ↔ 接口 |
| [docs/截图清单.md](docs/截图清单.md) | 软著/README 截图清单 |
| [docs/deployment-guide.md](docs/deployment-guide.md) | 部署与运维 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 如何贡献 |

### 关于部署（重要）

| 组件 | 可否部署到 Vercel |
|------|-------------------|
| 前端（静态） | ✅ 可以 |
| 后端 FastAPI / Celery / Redis / Postgres | ❌ 不可以（需 Docker 服务器 / Railway 等） |

可选：Vercel 仅托管前端，并设置 `VITE_API_BASE_URL` 指向已部署的 API。详见 [docs/deployment-guide.md](docs/deployment-guide.md)。  
**申请软著与开源演示均不强制公网部署。**

---

## 贡献

欢迎 Issue 与 PR。请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 安全

请勿在 Issue 中公开密钥。漏洞报告见 [SECURITY.md](SECURITY.md)。

## 许可证

[MIT](LICENSE) © 2026 AgentFlow-Eval Team

## 免责声明

运行评测将调用大模型 API，可能产生费用。请自行保管 `OPENAI_API_KEY`，切勿提交到 Git。
