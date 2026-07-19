# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 精神，版本号尽量遵循语义化版本。

## [Unreleased]

### Added

- **v1.0 阶段 5–6（Billing / Benchmark）**
  - Billing：Free/Pro/Enterprise 限额（task/token/storage/plugin）、`GET /billing/plan`、`POST /billing/webhook` 别名；超额 **429 QUOTA_EXCEEDED**；migration `014`
  - Benchmark 平台：`benchmarks`/`cases`/`runs`/`results`、import JSON/CSV、run→Evaluation Engine、leaderboard；前端 `/benchmarks`；migration `015`；文档 `docs/benchmarks.md`
- **v1.0 阶段 1–4（审计 / API Freeze / Tenant / RBAC）**
  - `PROJECT_STATUS.md` 全面审计
  - API 冻结：`docs/api-contract.md`、`docs/openapi-v1.json`、`scripts/export_openapi.py`、`test_api_contract.py`
  - 企业多租户：`tenants` / `tenant_members`、核心表 `tenant_id`、migration `013`、`X-Tenant-ID`、`/api/v1/tenants/*`、隔离测试
  - 企业 RBAC：`system_admin` / `tenant_admin` / `member` / `viewer` + 遗留别名；权限 `tenant:*` / `billing:*` / `benchmark:*`；`docs/rbac-enterprise.md`
- **落地加固（完整与可部署）**
  - 增强 `python -m app.core.seed`：COMPLETED 任务 + 成功/失败 Trace + MetricScore + AOLS `agent_logs`（驾驶舱/诊断/监控可开箱有数）
  - Dashboard AOLS 双源卡片：`/logs/statistics` → Events / Errors / Agent Fail；空库 EmptyState 引导 seed
  - 生产清单对齐 migration `012` 与演示就绪勾选；落地执行报告见 `docs/落地执行报告-完整与可部署.md`
- **AgentFlow Intelligence Center**：企业级 AI Agent 可观测 / 评测 / 诊断控制中心（Cyber Command 主题）
  - AI Dashboard 驾驶舱 `/dashboard`：Health Score、拓扑 ReactFlow、ECharts 趋势
  - Trace Explorer `/traces`：LangSmith 风格左右分栏
  - Failure Diagnosis Center `/diagnosis`：Agent Loop / Tool Failure / Token & Prompt Drift
  - Analytics `/analytics`：能力雷达、模型对比、热力图
  - Realtime Monitoring `/monitoring`：控制面状态与日志流
  - 右下角 AI Optimization Assistant
- **Phase 1 Design System**：`theme/tokens.ts` 单一色板；Command shell（`ic-shell`）；分组导航；统一 PageHeader/Empty/Skeleton；业务页 `ic-page` 皮肤
- **Dashboard + ECharts + ReactFlow 升级**
  - ORM 日级时序 `compute_dashboard_series`（tokens / latency / errors / success）
  - 双轴折线、Donut 状态分布、横向错误拓扑柱图、增强 Gauge
  - 水平 Pipeline 拓扑 + MiniMap + 图例 + 节点指标/脉冲
  - 驾驶舱 7/14/30d 窗口切换
- **Trace + Diagnosis + Analytics 升级**
  - Trace Explorer：Steps/DAG/Metrics 三栏、自动选中、Judge、深链 Diagnosis
  - Diagnosis：task/trace 双入口、置信度 Gauge、Evidence 折叠、Issue 筛选
  - Analytics：真实日级热力、雷达优先 metric_scores、模型分布无假数据垫底
- **Brand kit · AgentFlow Intelligence**
  - 矢量 Logo 体系：`frontend/public/assets/logo/`（mark / dark / light / favicon / animation）
  - `BrandLogo` + BootSplash；侧栏 / Loading / 404 / 标题 / README / BRAND-GUIDE 同步
- **AOLS 日志 Phase 2**：structlog 硬化、`LogEvent`、敏感字段脱敏、HTTP access 结构化日志、`error_id` / `X-Error-ID`
- **AOLS 日志 Phase 3**：Agent/LLM/Tool/Celery lifecycle 事件（`agent.*` / `llm.*` / `tool.*` / `evaluation.*`）、loop/timeout 检测
- **AOLS 日志 Phase 4**：`agent_logs` 表 + DB sink；`GET /api/v1/logs` / `statistics`；Monitoring 接真实日志流

- **Backend**：`GET /api/v1/dashboard` 驾驶舱总览；`/api/v1/diagnosis` 故障诊断；Trace 响应增强版本/Token/成本字段
- 开源元文件：`CONTRIBUTING.md`、`SECURITY.md`、Issue/PR 模板
- 文档中心：`docs/README.md`、功能模块清单、截图清单
- 部署环境模板：`backend/.env.docker.example`、生成脚本 `scripts/generate-deploy-env.ps1`
- README 重构：双启动路径（Docker / Eager）、明确 Vercel 仅前端
- **生产配置校验**（`settings_guard`）：`ENV=prod` 时拒绝弱 `SECRET_KEY` / `DEBUG=true` 等
- **健康探针**：`/health/live`（存活）与 `/health/ready`（就绪，失败返回 503）
- **安全响应头中间件**：nosniff / DENY frame / CSP / Permissions-Policy；生产环境 HSTS
- **评测流水线纯函数层**（`core/evaluation/pipeline.py`）：聚合与状态机可单测
- Judge 引擎：LRU 缓存、可配置超时回退规则分、CJK 分词与 bigram 相似度
- **HttpAgentRunner**：对接用户自有 Agent HTTP 服务（`agent_config.runner=http`）
- **Experiment 对比实验**：`/api/v1/experiments` 多变体跑分与 `/compare` 横向对比
- **check-prod**：`python -m app.cli.check_prod` / `make check-prod` 部署前配置检查
- **Prometheus 可观测性**：`GET /metrics`、HTTP/业务指标（任务、流水线、Judge、Token），文档见 `docs/observability.md`
- **RBAC 权限控制**：5 角色（ADMIN/MANAGER/REVIEWER/USER/GUEST）+ 权限矩阵、`@require_permission`、资源级校验，文档见 `docs/rbac.md`
- **弹性层**：tenacity 重试（最多 3 次指数退避）、熔断（5 次/60s）、30s 超时、LLM→规则降级；文档见 `docs/resilience.md`
- **数据库优化**：复合索引迁移 `007`、任务/实验列表去 N+1、SQLite WAL；文档见 `docs/database-optimization.md`
- **多级缓存**：L1 内存 + L2 Redis、Cache-Aside/Write-Through、列表版本失效、仪表板 `/dashboard/stats`、预热与 Prometheus 缓存指标；文档见 `docs/caching.md`
- **前端性能（Phase 3.3）**：Vite vendor 分包、React Query TTL 对齐后端、Dashboard 走 stats API、`memo`/路由 hover prefetch；文档见 `docs/frontend-performance.md`
- **多模态评估**：本地/S3 存储、图像/PDF/表格/文本提取、规则+Vision LLM 评分、`/api/v1/media/*`；文档见 `docs/multimodal.md`
- **A/B 测试框架**：粘性分流、exposure/conversion/metric、比例 z / Welch t、样本量估算、离线 Experiment 提升；文档见 `docs/ab-testing.md`
- **插件系统**：动态加载、生命周期、钩子（pre/post）、AgentRunner/Judge/Tool/Hook 扩展、本地市场目录与 API `/api/v1/plugins`；示例插件见 `app/plugins/examples/`；文档见 `docs/plugins.md`
- **可插拔基础设施（Ports & Adapters）**：`TaskQueuePort` / `CachePort` / `EventBusPort` / `MeteringPort`；Celery、Eager、Memory 队列适配器；`DEPLOY_PROFILE=lite|private|saas|auto`
- **Lite 极简部署**：零 Redis/Celery Worker（`scripts/start-lite.ps1`、`docker-compose.lite.yml`、`docs/deploy-profiles.md`）
- **前后端权限闭环**：`GET /api/v1/me`、前端 `AuthProvider` / `RouteGuard` / `Can` / 动态菜单
- **TraceID 透传**：`X-Request-ID` → contextvars + 响应 `X-Trace-ID`
- **SaaS 计费骨架**：plans/subscriptions/usage/quota/invoices（migration 010）、`/api/v1/billing/*`、execute 配额门闩（`BILLING_ENABLED`）
- **业务可观测**：`/api/v1/observability/kpis|slow-tasks|error-topology`；慢任务环形缓冲
- **插件商业化元数据**：versioning / commerce / sandbox；市场 `GET .../market/{id}/meta`
- **场景测试**：`tests/scenarios/test_eval_happy_path_lite.py`
- **计量绑定真实 actor**：suite/judge 从 Task.created_by 解析；`observe_*` 支持 `actor`/`ref_id`
- **额度账期 rollover**：`POST /billing/quota/rollover`；月度重置 API
- **402 超额 E2E 单测** + CI 纳入 `tests/scenarios`
- **慢任务持久化**：表 `slow_task_events`（migration 011），API `source=db|memory|auto`
- **TraceID 全链路**：execute enqueue 透传 `_trace_id` → worker suite/judge；audit 自动补 trace
- **错误拓扑指标**：`agentflow_stage_errors_total` / `agentflow_slow_tasks_total` + Grafana JSON
- **插件商业化运营**：权益硬校验、付费 mock `premium_length_judge`、sandbox 门闩、安装/启停审计、前端 `/plugins` 市场页
- **Stripe Checkout 占位**：`POST /billing/checkout`、`mock-confirm`、公开 webhook；前端付费套餐结账；默认 mock 无真实扣款
- **P0 交付闭环**：compose `migrate` 服务（alembic head）、`post-deploy-verify.ps1`、`demo-playbook.ps1`、`docs/DEMO.md` + `production-checklist.md`；健康探针 `/health/ready`
- **P2 体验加固**：Header 配额徽章；慢任务 API `source=auto|db`；`PLUGIN_STRICT_ALLOWLIST` / `PLUGIN_ALLOWLIST` 启动白名单

### Changed

- 前端 `services/*` 明确为 `api/*` 兼容层
- 演示种子数据增强（中英双语业务场景用例）
- Docker healthcheck 改为 `/health/ready`
- Celery 任务编排复用 pipeline 纯函数
- `build_agent_runner` 统一工厂（OpenAI ReAct / HTTP）

## [0.1.0] - 2026-07-14

### Added

- 评测任务 CRUD、用例上传（CSV/JSON）、执行/取消/归档
- OpenAI 兼容 ReAct Agent 执行器与工具沙箱
- Trace 存储、LLM-as-Judge、人工复核、报告接口
- Celery 异步流水线、Redis 事件、WebSocket 活动
- 鉴权（API Key）、租户隔离、审计日志、限流
- React 前端：总览、任务、详情 DAG、报告、设置
- Docker Compose 全栈、Alembic 迁移、CI 工作流
- 软件设计说明书、用户操作手册
- MIT License
