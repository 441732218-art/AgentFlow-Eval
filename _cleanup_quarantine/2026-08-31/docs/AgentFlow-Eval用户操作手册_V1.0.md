# AgentFlow-Eval V1.0 用户操作手册

> 版本：V1.0 | 日期：2026年8月 | 适用于软著申请材料

---

## 1. 引言

### 1.1 软件概述

AgentFlow-Eval V1.0 是一套面向 AI Agent 的自动化评测平台。用户可通过本系统对基于大语言模型（LLM）的智能代理（Agent）进行多维度性能评测，包括任务执行成功率、工具调用正确性、响应时间、Token 消耗等。系统支持离线实验对比、在线 A/B 测试、基准测试（Benchmark）以及多模态内容评测。

### 1.2 运行环境

| 环境项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| 操作系统 | Windows 10 / Ubuntu 20.04+ / macOS 12+ | Ubuntu 22.04 LTS |
| Python | 3.11+ | 3.12 |
| 数据库 | SQLite（开发）/ PostgreSQL 15+（生产） | PostgreSQL 16 |
| Redis | 6.0+ | 7.0+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 2 GB | 10 GB（含日志和媒体文件） |

### 1.3 技术栈

- **后端框架**：FastAPI（Python异步Web框架）
- **异步任务**：Celery + Redis
- **数据库ORM**：SQLAlchemy（异步模式）
- **API文档**：OpenAPI（自动生成 Swagger UI）
- **认证**：API Key / Bearer Token

---

## 2. 安装部署

### 2.1 部署步骤

**步骤1：获取源码并安装依赖**

```bash
cd AgentFlow-Eval/backend
pip install -r requirements.txt
```

**步骤2：配置环境变量**

在项目根目录创建 `.env` 文件：

```bash
ENV=dev
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./agentflow_eval.db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-your-key-here
AUTH_ENABLED=false
BILLING_ENABLED=false
```

### 2.2 关键配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ENV` | 运行环境（dev/test/prod） | dev |
| `DATABASE_URL` | 数据库连接串 | sqlite+aiosqlite:///... |
| `REDIS_URL` | Redis 连接串 | redis://localhost:6379/0 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | （空） |
| `AUTH_ENABLED` | 是否启用认证 | false |
| `BILLING_ENABLED` | 是否启用计费 | false |
| `PLUGINS_ENABLED` | 是否启用插件 | true |
| `LOG_LEVEL` | 日志级别 | INFO |

### 2.3 启动与停止

**启动（开发模式）：**

```bash
redis-server                                    # 终端1
celery -A app.core.celery_app.celery worker --loglevel=info  # 终端2
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload     # 终端3
```

或使用一体化脚本：`python _start_api.py`

**停止：** 按 `Ctrl+C` 依次停止 uvicorn 和 celery worker。

**验证：** 访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

[此处插入截图：Swagger API 文档首页]

---

## 3. 登录与首页

### 3.1 登录方式

- **无认证模式**（默认）：开发环境无需登录
- **API Key 认证**：生产环境通过 `X-API-Key` 请求头传递密钥

```bash
curl -H "X-API-Key: dev-secret" http://localhost:8000/api/v1/tasks
```

### 3.2 首页仪表盘

登录后首页展示核心统计指标：

| 指标 | 说明 |
|------|------|
| 任务总数 | 已创建的评测任务总量 |
| 运行中任务 | 当前正在执行的任务数 |
| 成功率 | 已完成任务中成功占比 |
| 平均响应时间 | 所有 Trace 的平均耗时（ms） |
| Token 消耗 | 今日累计 Token 用量 |

[此处插入截图：首页仪表盘]

---

## 4. 任务管理

### 4.1 功能概述

任务是核心操作单元。每个任务包含一组测试用例（TestSuite），系统自动执行每个用例并生成详细轨迹（Trace）和评分。

**任务状态流转：**
```
CREATED → QUEUED → RUNNING → JUDGING → COMPLETED
              ↘ FAILED / CANCELLED / TIMEOUT
```

### 4.2 创建评测任务

**操作步骤：**

1. 点击左侧导航「任务」
2. 点击右上角「创建任务」
3. 填写任务名称、描述、Agent 配置（JSON）

[此处插入截图：创建任务对话框]

**请求示例：**

```json
POST /api/v1/tasks
{
  "name": "GPT-4o 多步推理评测",
  "description": "评估 Agent 在复杂推理任务上的表现",
  "agent_config": {
    "model": "gpt-4o",
    "temperature": 0.3,
    "max_tokens": 4096,
    "runner": "openai",
    "tools": ["search", "calculator"]
  }
}
```

**参数说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| name | string | 是 | 任务名称，1-255字符 |
| description | string | 否 | 任务描述 |
| agent_config.model | string | 否 | 模型名称，默认 gpt-4o |
| agent_config.temperature | float | 否 | 温度参数 0-2，默认 0 |
| agent_config.max_tokens | int | 否 | 最大输出 Token 数 |
| agent_config.runner | string | 否 | 执行器类型（openai/http/http_agent） |
| agent_config.tools | array | 否 | 可用工具列表 |

**预期响应：**

```json
{
  "id": "task_abc123",
  "name": "GPT-4o 多步推理评测",
  "status": "created",
  "agent_config": {"model": "gpt-4o", "temperature": 0.3},
  "test_suite_count": 0,
  "created_at": "2026-08-08T10:00:00Z"
}
```

### 4.3 查看任务列表

支持按状态筛选（created/queued/running/completed）、分页浏览（每页默认20条）、按创建时间降序排列。

```json
GET /api/v1/tasks?page=1&page_size=20&status=running
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 任务唯一标识 |
| name | string | 任务名称 |
| status | string | 当前状态 |
| agent_config | object | Agent 配置快照 |
| test_suite_count | int | 关联测试用例数 |
| created_at | datetime | 创建时间 |

### 4.4 查看任务详情

点击任务名称进入详情页，可切换查看「测试用例」、「Trace 轨迹」、「日志」等标签页。

[此处插入截图：任务详情页]

### 4.5 取消/重跑任务

```json
PATCH /api/v1/tasks/{task_id}/status
{ "status": "cancelled" }
```

重跑：复制原任务 agent_config，重新创建即可。


---

## 5. A/B 测试（在线实验）

### 5.1 功能概述

A/B 测试允许为不同 Agent 配置创建变体（Variant），在实际流量中随机分配请求，统计转化率和响应时间，自动计算统计显著性（p值）和置信区间。

**实验状态流转：** `draft` → `running` → `completed` / `stopped`

### 5.2 创建 A/B 实验

1. 点击「A/B 测试」→「创建实验」
2. 填写实验键（key）、名称、变体列表

```json
POST /api/v1/ab
{
  "key": "model-comparison-v1",
  "name": "GPT-4o vs GPT-4o-mini 对比",
  "variants": [
    {"key": "gpt4o", "weight": 50, "is_control": true,
     "payload": {"model": "gpt-4o", "temperature": 0.3}},
    {"key": "gpt4o-mini", "weight": 50, "is_control": false,
     "payload": {"model": "gpt-4o-mini", "temperature": 0.3}}
  ],
  "primary_metric": "conversion",
  "alpha": 0.05, "min_sample_size": 100, "start_immediately": true
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| key | string | 是 | 实验唯一键，用于标识 |
| name | string | 是 | 实验名称 |
| variants | array | 是 | 变体配置，至少2个 |
| variants[].key | string | 是 | 变体标识 |
| variants[].weight | float | 是 | 流量权重（会归一化处理） |
| variants[].is_control | bool | 是 | 是否为对照组 |
| variants[].payload | object | 否 | 变体 Agent 配置 |
| primary_metric | string | 否 | 主要观测指标，默认 conversion |
| alpha | float | 否 | 显著性水平，默认 0.05 |
| min_sample_size | int | 否 | 最小样本量，默认 100 |

### 5.3 流量分配

调用分配接口为指定用户分配变体：

```json
POST /api/v1/ab/assign
{ "experiment_key": "model-comparison-v1", "user_id": "user_12345" }
```

系统根据变体权重随机分配，返回分配的变体 key 和配置。

### 5.4 查看实验结果

进入实验详情页查看各变体统计：样本量、转化率、p值、提升率。当 p < alpha 时结果具有统计显著性。

[此处插入截图：A/B 实验结果页]

### 5.5 暂停/结束实验

```json
PATCH /api/v1/ab/{experiment_id}/status
{ "status": "completed" }
```

---

## 6. 基准测试（Benchmark）

### 6.1 功能概述

基准测试提供标准化评测框架。创建包含固定测试用例集的基准（Benchmark），多次运行不同 Agent 配置，对比各次运行得分，实现回归检测和排行榜功能。

### 6.2 创建基准

**方式一：从已有任务复制用例**

```json
POST /api/v1/benchmarks
{ "name": "推理能力基准", "version": "1.0",
  "source_task_id": "task_abc123", "tags": ["reasoning", "math"] }
```

**方式二：手动添加用例**

```json
POST /api/v1/benchmarks
{ "name": "自定义基准",
  "cases": [
    {"user_query": "计算 123 x 456", "expected_output": "56088"},
    {"user_query": "法国的首都是？", "expected_output": "巴黎"}
  ]
}
```

### 6.3 执行基准

```json
POST /api/v1/benchmarks/{benchmark_id}/run
{ "label": "gpt-4o-run-1",
  "agent_config": {"runner": "openai", "model": "gpt-4o", "temperature": 0} }
```

### 6.4 查看运行历史与排行榜

- 运行历史：查看基准的所有运行记录及得分
- 排行榜：`GET /api/v1/benchmarks/{id}/leaderboard`，按得分降序排列

[此处插入截图：基准测试排行榜]

---

## 7. 实验对比（Experiment）

### 7.1 功能概述

创建离线实验组，包含多个变体配置（Run），系统自动为每个变体执行相同的测试用例集，最终对比各变体得分，识别最佳配置。

### 7.2 创建实验组

1. 点击「实验对比」→「创建实验」
2. 选择源任务（系统自动拷贝测试用例）
3. 添加变体 Runner 配置

```json
POST /api/v1/experiments
{
  "name": "多模型对比实验", "task_id": "task_abc123",
  "runs": [
    {"label": "gpt-4o", "agent_config": {"model": "gpt-4o", "temperature": 0}},
    {"label": "gpt-4o-mini", "agent_config": {"model": "gpt-4o-mini", "temperature": 0}},
    {"label": "claude-3.5", "agent_config": {"model": "claude-3-5-sonnet", "temperature": 0}}
  ]
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| name | string | 是 | 实验名称 |
| task_id | string | 是 | 源任务 ID |
| runs | array | 是 | 变体列表 |
| runs[].label | string | 是 | 变体标签（如模型名） |
| runs[].agent_config | object | 是 | 该变体的 Agent 配置 |

### 7.3 对比得分

```json
GET /api/v1/experiments/{experiment_id}/compare
```

返回各变体平均分、与最佳变体差异（delta）、排名，帮助快速定位最优配置。

---

## 8. 计费与配额

### 8.1 功能概述

计费系统（`BILLING_ENABLED=true` 时激活）支持多层级套餐，提供用量统计、配额管理、订阅升级等功能。默认套餐包括 Free、Pro 和 Enterprise。

### 8.2 套餐列表

| 套餐 | Token 配额 | 任务配额 | 存储配额 | 插件配额 |
|------|-----------|---------|---------|---------|
| Free | 100,000 | 50 | 100 MB | 3 |
| Pro | 1,000,000 | 500 | 1 GB | 10 |
| Enterprise | 10,000,000 | 5,000 | 10 GB | 无限制 |

### 8.3 操作接口

```json
GET  /api/v1/billing/plans     → 查看所有套餐
GET  /api/v1/billing/plan      → 查看当前套餐
GET  /api/v1/billing/quota     → 查看配额余额
GET  /api/v1/billing/usage     → 查看用量统计
POST /api/v1/billing/subscribe { "plan_code": "pro" }  → 订阅/升级套餐
POST /api/v1/billing/quota/rollover → 重置配额周期
GET  /api/v1/billing/invoices  → 查看账单
```





---

## 9. 用户与权限

### 9.1 角色定义

| 角色 | 权限范围 |
|------|----------|
| admin（系统管理员） | 全部权限，可管理用户和系统配置 |
| tenant_admin（租户管理员） | 管理租户内用户和资源 |
| manager（管理者） | 创建/修改/删除任务，查看报告 |
| reviewer（评审者） | 查看任务、人工审核评分 |
| member（成员，默认） | 创建任务、查看自己的任务 |
| viewer（观察者） | 只读访问 |

### 9.2 权限矩阵

| 操作 | admin | manager | member | viewer |
|------|:--:|:--:|:--:|:--:|
| 创建任务 | ✅ | ✅ | ✅ | ❌ |
| 查看所有任务 | ✅ | ✅ | ❌ | ✅ |
| 修改/删除任务 | ✅ | ✅ | ❌ | ❌ |
| 执行任务 | ✅ | ✅ | ✅ | ❌ |
| 管理插件 | ✅ | ❌ | ❌ | ❌ |
| 系统配置 | ✅ | ❌ | ❌ | ❌ |
| 查看审计日志 | ✅ | ✅ | ❌ | ❌ |

### 9.3 配置方式

通过环境变量配置：`ACTOR_ROLES="alice:admin,bob:manager"`，默认角色由 `DEFAULT_ROLE` 控制（默认 member）。

---

## 10. 观测性与诊断

### 10.1 系统日志

`GET /api/v1/logs` 查看结构化日志，支持按级别（DEBUG/INFO/WARNING/ERROR）、时间范围过滤。

### 10.2 慢任务记录

`GET /api/v1/observability/slow-tasks` 查看执行时间超过阈值（默认 30 秒）的任务。

### 10.3 KPI 指标

`GET /api/v1/observability/kpis`

| 指标 | 说明 |
|------|------|
| success_rate | 任务成功率（%） |
| avg_response_time_ms | 平均响应时间（毫秒） |
| total_tokens | Token 总消耗 |
| active_tasks | 当前活跃任务数 |

### 10.4 诊断工具

`POST /api/v1/diagnosis` 自检：数据库、Redis、Celery、OpenAI API 连通性。

---

## 11. 插件管理

插件系统支持动态加载三类扩展：**Runner**（执行器）、**Judge**（评判器）、**Tool**（工具）。

```json
GET    /api/v1/plugins           → 列出插件
PATCH  /api/v1/plugins/{id}      → 启用/禁用
POST   /api/v1/plugins/market    → 浏览插件市场
```

**添加自定义插件：** 在 `app/plugins/examples/` 下创建 Python 文件，继承基类实现接口，重启自动加载。

[此处插入截图：插件管理页]

---

## 12. 多媒体处理

支持上传图片（jpg/png）、PDF、电子表格（xlsx/csv），自动提取文本和特征。

```json
POST /api/v1/media/upload      → 上传（multipart/form-data）
GET  /api/v1/media/{id}        → 查看提取结果
```

多模态评测：agent_config 配置 `"multimodal": true, "media_ids": ["media_xxx"]`。

---

## 13. HTTP Agent 探测

验证外部 HTTP Agent 端点连通性、协议兼容性和 SSRF 安全性。

```json
POST /api/v1/agents-http/probe
{ "endpoint_url": "https://agent.example.com/v1/invoke",
  "method": "POST", "query": "ping", "timeout_sec": 10 }
```

返回：ok / reachable / protocol_compatible / ssrf_blocked / latency_ms。

---

## 14. 设置

| 配置分类 | 关键配置项 |
|----------|-----------|
| 通用 | ENV, DEBUG |
| 数据库 | DATABASE_URL |
| 模型 | OPENAI_API_KEY, OPENAI_BASE_URL |
| 认证 | AUTH_ENABLED, API_KEYS |
| 计费 | BILLING_ENABLED |
| 插件 | PLUGINS_ENABLED, PLUGIN_DIRS |
| 日志 | LOG_LEVEL, LOG_FORMAT |
| 性能 | RATE_LIMIT_DEFAULT |

通过 `.env` 文件或环境变量修改。

---

## 15. 常见问题与故障排除

### 15.1 任务持续 "queued" 状态
**原因：** Celery Worker 或 Redis 未运行。
**解决：** `redis-cli ping`；检查 celery worker 进程。

### 15.2 创建任务报 401 错误
**原因：** 认证已启用但未提供有效 API Key。
**解决：** 添加 `X-API-Key` 请求头；检查 `API_KEYS` 配置。

### 15.3 评测结果异常
**原因：** API Key 无效、模型名称错误或网络不通。
**解决：** 检查 `OPENAI_API_KEY`；查看 Trace 日志；运行 `POST /api/v1/diagnosis`。

### 15.4 上传媒体失败
**原因：** 格式不支持或 PDF 为扫描版。
**解决：** 支持 jpg/png/pdf/xlsx/csv/txt；PDF 需可提取文本。

### 15.5 插件加载失败
**原因：** 目录不存在或代码有语法错误。
**解决：** 检查 `PLUGIN_DIRS` 配置；`python -m py_compile plugin.py` 验证语法。

### 15.6 数据库连接失败
**原因：** PostgreSQL 服务未启动。
**解决：** 切换到 SQLite：`DATABASE_URL=sqlite+aiosqlite:///./agentflow_eval.db`。

---

> **文档结束** | AgentFlow-Eval V1.0 用户操作手册 | © 2026
