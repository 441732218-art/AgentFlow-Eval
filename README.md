<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <a href="https://github.com/441732218-art/AgentFlow-Eval/actions">
    <img src="https://github.com/441732218-art/AgentFlow-Eval/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
</p>
# AgentFlow-Eval

面向业务场景的 **Agent 自动化评测工作台**。

## 项目概述

AgentFlow-Eval 是一个企业级 Web 应用，用于评测 AI Agent 在执行复杂业务任务时的表现。核心价值是提供**可视化的执行链路追踪**和**自定义业务指标打分**。

> 目标用户：企业 AI 应用开发者
> 核心场景：上传业务测试用例 → 自动运行 Agent → 可视化展示执行链路 → 生成评测报告

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 后端框架 | FastAPI + Uvicorn | Python 异步 Web 框架 |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） | ORM: SQLAlchemy 2.0 |
| 任务队列 | Celery + Redis | 处理异步评测任务 |
| 前端框架 | React 18 + TypeScript + Vite | 组件库: Ant Design 5.0 |
| 可视化 | ReactFlow | Agent 执行链路 DAG 图 |
| 状态管理 | Zustand | 轻量级状态管理 |
| 大模型 | OpenAI SDK | Agent 执行和 LLM-as-Judge |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- Redis（可选，见下方「本地评测模式」说明）

### 本地评测模式（无需 Redis）

若本地不启动 Redis / Celery Worker，可在 `backend/.env` 中设置：

```bash
CELERY_TASK_ALWAYS_EAGER=true
```

任务会在 API 进程内同步执行，适合本地开发与调试。生产环境请保持 `false` 并使用 Redis + Celery Worker。

### Windows 一键启动

已在本机准备好 venv / `.env`（Eager 模式）后，可直接：

```powershell
# 分别打开后端 + 前端两个窗口
powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1

# 或分终端手动：
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1
powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1
```

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY
# 本地无 Redis 时，设置 CELERY_TASK_ALWAYS_EAGER=true

# 启动服务
uvicorn app.main:app --reload --port 8000
```

API 文档访问 http://localhost:8000/docs

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173
### 运行测试

```bash
# 后端单元测试（22 个）
cd backend
pytest tests/unit/ -v

# 带覆盖率报告
pytest tests/unit/ --cov=app --cov-report=term-missing

# 后端 API E2E
pytest tests/test_e2e.py -v

# 前端单元测试
cd frontend
npm test

# 前端 E2E（需先启动前后端，或依赖 playwright webServer）
npm run test:e2e
```

## 在线预览

启动后访问：
- 前端界面：http://localhost:5173
- API 文档：http://localhost:8000/docs
- Celery 监控（Flower）：http://localhost:5555（Docker 环境）


### Docker 启动（Redis + PostgreSQL）


```bash
cd backend
docker-compose up -d
```

## 项目结构

```
AgentFlow-Eval/
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口
│   │   ├── config.py     # 配置管理
│   │   ├── api/v1/       # API 路由
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── core/         # 核心业务逻辑
│   │   │   ├── agent_runner/    # Agent 执行器
│   │   │   ├── judge_engine/    # LLM-as-Judge 打分引擎
│   │   │   └── celery_app/      # Celery 任务队列
│   │   └── utils/        # 工具函数
│   ├── alembic/          # 数据库迁移
│   └── docker-compose.yml
├── frontend/              # React 前端
│   └── src/
│       ├── pages/        # 页面组件
│       ├── services/     # API 调用
│       ├── stores/       # Zustand 状态管理
│       ├── types/        # TypeScript 类型
│       └── utils/        # 工具函数
└── docs/                 # 文档
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/tasks | 任务列表（默认隐藏已归档） |
| POST | /api/v1/tasks | 创建任务 |
| GET | /api/v1/tasks/{id} | 任务详情 |
| DELETE | /api/v1/tasks/{id} | 删除任务 |
| POST | /api/v1/tasks/{id}/execute | 执行评测 |
| POST | /api/v1/tasks/{id}/test-suites | 批量创建测试用例 |
| POST | /api/v1/tasks/{id}/test-suites/upload | 上传 CSV/JSON 导入用例 |
| POST | /api/v1/tasks/{id}/cancel | 取消任务 |
| POST | /api/v1/tasks/{id}/archive | 软归档任务 |
| POST | /api/v1/tasks/{id}/unarchive | 取消归档 |
| GET | /api/v1/traces | 轨迹列表 |
| GET | /api/v1/traces/{id} | 轨迹详情 |
| POST | /api/v1/traces/{id}/judge | LLM 评分 |
| POST | /api/v1/traces/{id}/review | 人工审核覆盖评分 |
| GET | /api/v1/reports/{id} | 任务报告 |
| GET | /api/v1/audit | 审计日志列表 |
| GET | /api/v1/tools | 内置沙箱工具列表 |
| POST | /api/v1/tools/probe | 调试执行沙箱工具 |
| GET | /api/v1/settings/actor | 当前 actor / is_admin |
| GET | /api/v1/settings | 公开设置摘要 |

### Celery 流水线测试

```bash
cd backend
set PYTHONPATH=.
pytest app/core/celery_app/tests/ --cov=app.core.celery_app.tasks --cov-fail-under=70 -v
```

### 鉴权（可选）

默认 `AUTH_ENABLED=false`（本地开发）。生产可在 `backend/.env` 中开启：

```bash
AUTH_ENABLED=true
API_KEYS=dev-secret:alice,ops-secret:ops
```

请求头二选一：

- `X-API-Key: dev-secret`
- `Authorization: Bearer dev-secret`

前端在「设置」页填写 API Key 后会自动附带到请求。

### 轻量多租户（按 actor 隔离）

开启 `AUTH_ENABLED=true`（或单独 `TENANCY_ENABLED=true`）后：

- 创建任务时写入 `created_by`（来自 API Key 映射的 actor 名）
- 列表 / 详情 / 执行 / 删除 / 报告等只可见自己的任务
- **Trace** 列表/详情/Judge/人工审核同样按所属 Task 的 `created_by` 隔离
- 越权访问返回 **404**（避免资源枚举）
- `ADMIN_ACTORS=admin` 中的 actor 可查看全部任务
- 前端任务列表 / 详情 / 总览展示 **Owner**（`created_by`）

```bash
AUTH_ENABLED=true
API_KEYS=alice-secret:alice,bob-secret:bob,ops-secret:admin
ADMIN_ACTORS=admin
```

### 工具沙箱

Agent 工具执行经 `tool_sandbox`：

- 仅允许注册表内工具（calculator / web_search 模拟 / current_datetime / json_get / regex_extract）
- 无网络、无文件系统、无任意代码执行
- 超时与输出截断

## 核心评分算法

LLM-as-Judge 的多维度评分引擎（`judge_engine/llm_judge.py`）：

1. **工具调用准确率**（40分）：检查实际工具调用是否匹配预期
2. **答案准确性**（40分）：LLM 判断最终回复是否包含核心信息
3. **推理链路合理性**（20分）：是否存在无意义的重复思考或错误推理

---

© 2026 AgentFlow-Eval

---

<div align="center">
  <sub>Built with ❤️ by AgentFlow-Eval Team · © 2026</sub>
</div>
