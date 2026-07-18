# AgentFlow-Eval 文档中心

本目录汇总产品说明、软著材料与部署指引。**本地 Docker 或 Eager 模式即可完整体验，不强制公网部署。**

## 上手

| 文档 | 说明 |
|------|------|
| [../README.md](../README.md) | 项目首页、快速开始、API 摘要 |
| [brand/BRAND-GUIDE.md](brand/BRAND-GUIDE.md) | Logo / 色彩 / 品牌视觉规范 |
| [DEMO.md](DEMO.md) | 15 分钟演示剧本（Lite / Docker） |
| [production-checklist.md](production-checklist.md) | 生产上线检查清单（P0） |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 开发与贡献流程 |

## 项目审查与总览

| 文档 | 说明 |
|------|------|
| [**项目全面审查报告.md**](项目全面审查报告.md) | **全量审查归档**：功能、成熟度、进度、缺口、分阶段升级方案（推荐查阅） |
| [**Phase-A-提交与执行清单.md**](Phase-A-提交与执行清单.md) | Phase A：按主题拆分的 git 提交批次 + seed/日志卡片/E2E 验收 |
| [项目报告.md](项目报告.md) | 产品概述版项目报告（软著/对外叙事） |

## 软著与设计材料

| 文档 | 说明 |
|------|------|
| [软件设计说明书.md](软件设计说明书.md) | 架构、模块、技术选型 |
| [用户操作手册.md](用户操作手册.md) | 界面操作说明 |
| [功能模块清单.md](功能模块清单.md) | 模块 ↔ 源码目录 ↔ 主要接口 |
| [截图清单.md](截图清单.md) | 建议截取的运行画面（6～8 张） |

## 部署与运维

| 文档 | 说明 |
|------|------|
| [deployment-guide.md](deployment-guide.md) | 服务器 / CI 部署 |
| [observability.md](observability.md) | Prometheus 指标、`/metrics`、PromQL 示例 |
| [rbac.md](rbac.md) | RBAC 角色/权限矩阵、API Key 角色绑定 |
| [resilience.md](resilience.md) | 重试 / 熔断 / 超时 / LLM 降级 |
| [database-optimization.md](database-optimization.md) | 索引、N+1 消除、连接池与 SQLite WAL |
| [caching.md](caching.md) | 多级缓存、TTL 策略、失效与预热 |
| [frontend-performance.md](frontend-performance.md) | 前端分包、RQ 缓存、memo、prefetch |
| [multimodal.md](multimodal.md) | 多模态上传/提取/视觉评估、MinIO/S3 |
| [ab-testing.md](ab-testing.md) | 在线 A/B 分流、事件、显著性、与离线实验联动 |
| [plugins.md](plugins.md) | 插件系统：加载、钩子、Runner/Judge/Tool 扩展、本地市场 |
| [deploy-profiles.md](deploy-profiles.md) | 三级部署：lite / private / saas，Ports 与 TaskQueue |
| [billing.md](billing.md) | SaaS 套餐 / 用量 / 配额 / 账单 API |
| [observability-kpis.md](observability-kpis.md) | 业务 KPI、慢任务持久化、TraceID 全链路、错误拓扑 |
| [grafana-agentflow.json](grafana-agentflow.json) | Grafana 面板导入（Prometheus） |
| [vercel-postgres-self-api.md](vercel-postgres-self-api.md) | Vercel 前端 + 自备 API + Postgres |
| [../scripts/SERVER_DEPLOY.txt](../scripts/SERVER_DEPLOY.txt) | 云主机 Docker 命令备忘 |

### 部署边界（必读）

| 组件 | Vercel | 云主机 Docker | 本机 Eager |
|------|--------|---------------|------------|
| React 前端 | ✅ | ✅（compose 内 nginx） | ✅（Vite） |
| FastAPI | ❌ | ✅ | ✅ |
| Celery / Redis | ❌ | ✅ | Eager 可省略 |
| PostgreSQL | 托管库可选 | ✅ | SQLite 可替代 |

Vercel **仅适合静态前端**。后端请使用本机、VPS Docker 或 Railway 等。详见 README「关于部署」。

## 环境变量模板

见仓库根目录与 `backend/`、`frontend/` 下的 `*.example` 文件；由 `scripts/generate-deploy-env.ps1` 生成本地密钥文件（不入库）。
