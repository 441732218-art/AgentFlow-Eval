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

企业级 **Agent 评测与可观测平台**（仓库：`AgentFlow-Eval`）。

把任意 Agent（内置 OpenAI ReAct 或 **你自己的 HTTP 服务**）接入同一条流水线：  
**用例 → 执行 → Trace → 可配置 Judge → 多变体对比 → 驾驶舱诊断。**

> **无需公网部署即可完整体验。** 推荐 Lite / Eager 本地一键，或 Docker 私有化全栈。  
> 品牌：[`docs/brand/`](docs/brand/) · 协议：[`docs/http-agent-protocol.md`](docs/http-agent-protocol.md)

---

## 为什么选它

| 能力 | 说明 |
|------|------|
| **外部 Agent 接入** | `HttpAgentRunner` + Probe + SSRF 防护；统一 `run(query, tools, agent_config)` 契约 |
| **多变体对比** | Experiment：同一套用例、多种配置，并排看平均分 / 维度 / Token / 耗时 |
| **可配置评分卡** | Scorecard 定义维度与权重（默认 40/40/20），真正进入 Judge 规则与 LLM 路径 |
| **可观测闭环** | Trace DAG、故障诊断、AOLS 日志、Dashboard KPI |
| **可交付** | Docker / Lite、Web·PWA、Electron 桌面、离线包脚本 |

---

## 核心能力（产品向）

### 1. HTTP Agent 接入

- 任务创建时选择 **Runner = HTTP**，填写 `endpoint_url` / headers / timeout  
- **探测（Probe）**：`POST /api/v1/agents/http/probe` 校验可达性与协议兼容  
- **SSRF 默认开启**：拒绝内网、localhost、危险 scheme  
- 协议 **agentflow.http.v1**：见 [docs/http-agent-protocol.md](docs/http-agent-protocol.md)

### 2. Experiment 多变体对比

- 从已有任务克隆用例 → 多个 `agent_config` 变体并行评测  
- UI：侧栏 **对比实验** → 列表 / 创建 / 详情对比表（Best、Δ、维度分）  
- API：`/api/v1/experiments`、`/compare`

### 3. 可配置 Judge 评分卡

- 默认三维：`tool_accuracy` · `answer_correctness` · `reasoning_coherence`（权重 40/40/20）  
- 自定义写入 `Task.agent_config.scorecard`，规则路径与 LLM refine **均按权重计分**  
- 默认卡与校验：`GET /api/v1/judges/scorecards/default`

### 4. 评测主链路（不变）

任务管理 · CSV/JSON 用例 · 异步/Eager 执行 · Trace · 报告 · 审计 · RBAC

---

## 架构一览

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend · Vite + Ant Design                                  │
│  驾驶舱 · 任务 · Trace · 对比实验 · 报告 · 设置                    │
└────────────────────────────┬─────────────────────────────────┘
                             │  REST / WS  /api/v1
┌────────────────────────────▼─────────────────────────────────┐
│  FastAPI                                                       │
│  tasks · experiments · agents/http · judges · traces · …       │
└───────┬──────────────────────────────┬───────────────────────┘
        │                              │
   Runner 工厂                    Postgres / SQLite
   openai | http | plugin               │
        │                         Redis + Celery（可选）
        ▼
   Trace → Scorecard Judge → MetricScore → Experiment Compare
```

---

## 5 分钟上手

### 路径 A：Lite（零 Redis，最快）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-lite.ps1
```

另开终端写入演示数据：

```powershell
cd backend
# 激活 venv 后
python -m app.core.seed --force
```

| 地址 | 用途 |
|------|------|
| http://127.0.0.1:5173 | 前端 |
| http://127.0.0.1:8000/docs | OpenAPI |
| http://127.0.0.1:8000/health/ready | 就绪探针 |

### 路径 B：Docker 全栈

```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate-deploy-env.ps1
# 编辑 backend/.env.docker 填入 OPENAI_API_KEY
powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1
docker compose --env-file backend/.env.docker exec backend python -m app.core.seed --force
```

### Seed 之后建议点开

1. **驾驶舱** `/dashboard` — 非空 KPI / 活动  
2. **对比实验** `/experiments` — 查看 demo 多变体对比（Best / 维度分）  
3. **任务** — 打开「客服 Agent 综合评测（Demo）」看 Trace 与评分卡  
4. **创建任务** — 切换 HTTP Runner 或编辑评分卡 JSON  

---

## 快速开始（完整）

| 形态 | 命令 | 依赖 |
|------|------|------|
| **Lite** | `scripts\start-lite.ps1` | Python + Node |
| **Eager 本地** | 下方「方式 B」 | SQLite + Eager |
| **Private Docker** | `scripts\docker-up.ps1` | Postgres + Redis + Celery |

| 文档 | 说明 |
|------|------|
| [docs/DEMO.md](docs/DEMO.md) | 演示剧本 |
| [docs/deploy-profiles.md](docs/deploy-profiles.md) | lite / private / saas |
| [docs/production-checklist.md](docs/production-checklist.md) | 生产检查 |

### 方式 B：本地 Eager

```bash
cd backend && python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY + CELERY_TASK_ALWAYS_EAGER=true
uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev
```

```bash
cd backend && python -m app.core.seed --force
```

---

## 跨端交付

| 形态 | 入口 |
|------|------|
| Web / PWA | `cd frontend && npm run build:web` |
| 桌面安装包 | `scripts\build-release.ps1 -Targets web,desktop` |
| 发行说明 | [GitHub Releases v1.0.0](https://github.com/441732218-art/AgentFlow-Eval/releases/tag/v1.0.0) |
| 打包说明 | [docs/跨端打包与安装交付.md](docs/跨端打包与安装交付.md) |

---

## 环境变量（摘要）

| 文件 | 用途 | 提交 Git |
|------|------|----------|
| `backend/.env` / `.env.example` | 本地开发 | 仅 example |
| `backend/.env.docker` / `.env.docker.example` | Compose | 仅 example |
| `frontend/.env.local` | `VITE_API_BASE_URL` | 否 |
| `HTTP_AGENT_ALLOW_PRIVATE_IP` | 实验室放开 SSRF（**生产保持 false**） | — |

---

## 项目结构（节选）

```
AgentFlow-Eval/
├── backend/app/
│   ├── api/v1/endpoints/     # tasks, experiments, agents_http, judges, …
│   ├── core/
│   │   ├── agent_runner/     # 统一契约 · HTTP · SSRF · protocol v1
│   │   ├── judge_engine/     # Scorecard · LLMJudge
│   │   ├── evaluation/       # pipeline · compare
│   │   └── seed.py           # 演示任务 + 多变体实验
│   └── models/
├── frontend/src/
│   ├── pages/tasks|experiments|…
│   └── api/endpoints/
├── docs/                     # 协议 · 部署 · 软著材料
└── scripts/                  # 启动 / 打包 / 校验
```

---

## 主要 API

完整文档：http://localhost:8000/docs

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/v1/tasks` | 任务 |
| POST | `/api/v1/tasks/{id}/execute` | 执行 |
| GET/POST | `/api/v1/experiments` | 对比实验 |
| GET | `/api/v1/experiments/{id}/compare` | 侧向对比 |
| POST | `/api/v1/agents/http/probe` | HTTP Agent 探测 |
| GET | `/api/v1/agents/http/contract` | 协议摘要 |
| GET | `/api/v1/judges/scorecards/default` | 默认评分卡 |
| GET | `/api/v1/traces/{id}` | Trace |
| GET | `/api/v1/reports/{id}` | 报告 |

---

## 测试与 CI

```bash
cd backend && pytest tests/unit/ -q
cd frontend && npm test
```

CI：`.github/workflows/ci.yml` · Docker / 桌面构建见 `.github/workflows/`。

---

## 文档

| 文档 | 说明 |
|------|------|
| [docs/http-agent-protocol.md](docs/http-agent-protocol.md) | HTTP Agent 协议 + Probe + SSRF |
| [docs/DEMO.md](docs/DEMO.md) | 演示路径 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | 部署 |
| [docs/功能模块清单.md](docs/功能模块清单.md) | 模块 ↔ 源码 |
| [docs/releases/v1.0.0.md](docs/releases/v1.0.0.md) | v1.0.0 发布说明 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [SECURITY.md](SECURITY.md) | 安全 |

前端可部署 Vercel；后端需 Docker / 自托管 API。软著与演示**不强制**公网部署。

---

## 贡献 · 安全 · 许可

- 欢迎 Issue / PR · [CONTRIBUTING.md](CONTRIBUTING.md)  
- 勿公开密钥 · [SECURITY.md](SECURITY.md)  
- [MIT](LICENSE) © 2026 AgentFlow  

**免责声明：** 评测可能调用大模型 API 并产生费用；请自行保管 `OPENAI_API_KEY`。
