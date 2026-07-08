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
- Redis（可选，本地评测模式不需要）

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
| GET | /api/v1/tasks | 任务列表 |
| POST | /api/v1/tasks | 创建任务 |
| GET | /api/v1/tasks/{id} | 任务详情 |
| DELETE | /api/v1/tasks/{id} | 删除任务 |
| POST | /api/v1/tasks/{id}/execute | 执行评测 |
| GET | /api/v1/traces | 轨迹列表 |
| GET | /api/v1/traces/{id} | 轨迹详情 |
| POST | /api/v1/traces/{id}/judge | LLM 评分 |
| GET | /api/v1/reports/{id} | 任务报告 |

## 核心评分算法

LLM-as-Judge 的多维度评分引擎（`judge_engine/llm_judge.py`）：

1. **工具调用准确率**（40分）：检查实际工具调用是否匹配预期
2. **答案准确性**（40分）：LLM 判断最终回复是否包含核心信息
3. **推理链路合理性**（20分）：是否存在无意义的重复思考或错误推理

---

© 2026 AgentFlow-Eval
