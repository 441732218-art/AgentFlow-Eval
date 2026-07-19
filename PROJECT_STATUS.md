# AgentFlow-Eval — PROJECT STATUS（v1.0 发布前审计）

| 属性 | 内容 |
|------|------|
| **审计日期** | 2026-07-19 |
| **范围** | backend / frontend / scripts / docs / Docker / CI |
| **基线** | CHANGELOG Unreleased + 运行中 private Docker 栈 |
| **目标** | 企业级 Agent Evaluation Platform **v1.0 可发布** |
| **本文件性质** | **第一阶段只读审计**（后续阶段在此基线上增量实现） |

---

## 1. 执行摘要

AgentFlow-Eval 已是功能面较完整的 **高级技术 Demo / Private Preview**：

- 评测主链路（任务 → 执行 → Trace → Judge → 报告）**可跑通**
- Intelligence Center UI、AOLS、RBAC（actor 级）、计费骨架、插件、Ports/Adapters **已落地**
- Docker 一键（lite / private）、健康探针、迁移 001–012 **可用**

距离「企业级 v1.0 可公开发布」的**硬缺口**（按你方路线图）：

| 缺口 | 当前状态 | v1.0 要求 |
|------|----------|-----------|
| **企业多租户** | 仅 `created_by` actor 隔离 | `tenants` + `tenant_id` + `X-Tenant-ID` |
| **RBAC 企业角色** | admin/manager/reviewer/user/guest | system_admin / tenant_admin / member / viewer 等 |
| **API 契约冻结** | 运行时 `/docs` only | `api-contract.md` + `openapi-v1.json` + 兼容检查 |
| **Billing 商业闭环** | Mock Checkout / Stripe 占位 | 完整 plans/订阅/发票/配额 429 |
| **Benchmark 平台** | **不存在** | benchmarks 全栈 |
| **安全 hardening** | 部分中间件 + bandit（非阻断） | OWASP + 镜像非 root + 扫描门禁 |
| **CI 覆盖门禁** | `--cov-fail-under=35` | 目标 >80% |
| **Docker 生产级** | root 运行、无资源限制、无内置 prom/grafana | multi-stage、非 root、limits |

**综合成熟度（审计口径）**：约 **3.5 / 5 ★**（Preview 强，SaaS 发布未达标）。

---

## 2. 当前完成模块

### 2.1 后端（`backend/app`）

| 模块 | 路径线索 | 成熟度 |
|------|----------|--------|
| 评测任务 / 用例 / 执行 | `api/v1/endpoints/tasks.py`, `core/evaluation/`, `celery_app/` | **完成** |
| Trace / Judge / 人工复核 | `endpoints/traces.py`, `judge_engine/` | **完成** |
| 报告 | `endpoints/reports.py` | **完成** |
| Dashboard / Diagnosis / Logs | `dashboard.py`, `diagnosis.py`, `logs.py` | **完成** |
| Experiments / A/B / Media | `experiments.py`, `ab.py`, `media.py` | **完成** |
| API Key 鉴权 | `core/security.py`, `middleware.APIKeyAuthMiddleware` | **完成** |
| RBAC（5 角色） | `core/rbac.py` | **部分**（非企业角色集） |
| Actor 隔离 | `core/tenancy.py` + `Task.created_by` | **部分**（非 tenant 表） |
| Billing 骨架 | `models/billing.py`, `core/billing/`, `endpoints/billing.py` | **部分**（mock） |
| 插件 + 白名单 | `core/plugins/`, `PLUGIN_STRICT_ALLOWLIST` | **部分**（无签名校验） |
| Ports & Profiles | `core/ports/`, `profiles/` lite\|private\|saas | **完成** |
| 审计日志 | `models/audit_log.py`, `endpoints/audit.py` | **完成** |
| 可观测 Prometheus | `observability/`, `GET /metrics` | **完成** |
| 迁移 | `alembic/versions/001`–`012` | **完成** |

### 2.2 API 前缀（`/api/v1/*`）

已注册路由器：`me`, `billing`, `observability`, `tasks`, `dashboard`, `diagnosis`, `logs`, `media`, `ab`, `experiments`, `traces`, `reports`, `audit`, `tools`, `plugins`, `settings`, `ws`。

约 **70+** HTTP 路由（含 WS）。**无** `/tenants`、`/benchmarks`。

### 2.3 前端（`frontend/src`）

| 模块 | 状态 |
|------|------|
| Dashboard / Traces / Diagnosis / Analytics / Monitoring | **完成** |
| Tasks / Reports / Settings / Plugins / Billing | **完成** |
| AuthProvider / RouteGuard / Can | **完成**（API Key + 权限字符串） |
| Benchmarks UI | **缺失** |
| Tenant 切换器 | **缺失** |
| 单元测试 | 极少（`format.test.ts`, `performance.test.ts`） |
| E2E | `e2e/tasks.spec.ts` 骨架 |

### 2.4 部署 / 工程化

| 项 | 状态 |
|----|------|
| `docker-compose.yml` / `.lite` / `.prod` | **有** |
| `scripts/start-docker-stack.ps1` / lite / post-deploy-verify | **有** |
| CI: `.github/workflows/ci.yml`（ruff/pytest/bandit） | **有**（bandit/mypy 非阻断） |
| `build.yml` GHCR push | **有** |
| `deploy.yml` SSH | **有**（依赖 secrets） |
| 镜像非 root / multi-stage backend | **缺失** |
| Compose 内 Prometheus/Grafana | 仅 `docs/grafana-agentflow.json`，**未**进 compose |
| 环境模板 | `.env.example` / `.env.docker.example` / `deploy.env.example` |

### 2.5 测试

- 后端 unit/scenario：**~51** 个 `test_*.py`
- 覆盖门禁 CI：`--cov-fail-under=35`（远低于 80%）
- 已有：`test_tenancy.py`, `test_rbac.py`, `test_billing*.py`, `test_security.py`
- **无** tenant 表级隔离测试、**无** API contract freeze 测试

---

## 3. 未完成模块（相对 v1.0 目标）

| 优先级 | 模块 | 说明 |
|--------|------|------|
| P0 | **API Freeze** | 无 `docs/api-contract.md` / `openapi-v1.json` / 兼容检查 |
| P0 | **Enterprise Tenant** | 无 `tenants` / `tenant_members` / `tenant_id` / `X-Tenant-ID` |
| P0 | **RBAC 企业升级** | 角色与权限矩阵未达 system_admin / tenant_* / billing&benchmark perms |
| P1 | **Billing 商业化** | Free/Pro/Enterprise 产品化、429 QUOTA、Stripe 真实路径 |
| P1 | **Benchmark 平台** | 全栈缺失 |
| P1 | **安全审计闭环** | trivy/semgrep/pip-audit 未强制；Docker root；插件签名无 |
| P2 | **生产 Docker** | Dockerfile.backend 拆分、资源限制、观测栈 |
| P2 | **CI/CD 发布** | release.yml 语义化、镜像扫描阻断、覆盖率 80% |
| P2 | **配置三分** | `.env.lite|private|saas.example` 未齐 |

---

## 4. 技术债务

1. **租户模型混用**：`created_by` actor 与未来 `tenant_id` 需兼容迁移，避免破坏 Lite。
2. **OpenAPI 非冻结**：Pydantic 响应模型覆盖不全，部分 endpoint 返回裸 `dict`。
3. **RBAC 命名**：`admin`/`user`/`guest` 与企业术语不一致，前端 `permissions.ts` 需同步。
4. **CI 门禁过低**：35% coverage、bandit `continue-on-error`。
5. **密钥 UX**：private Docker `AUTH_ENABLED=true` 时前端依赖 runtime-config / 设置页（已部分修复）。
6. **版本叙事**：软著 V1/V2、开源 0.1.0、Unreleased 未统一到 **v1.0.0**。
7. **后端 Dockerfile 非 multi-stage / 无 USER**。
8. **前端测试几乎空白**。

---

## 5. 安全风险

| 等级 | 风险 | 说明 |
|------|------|------|
| **High** | 容器默认 root | `backend/Dockerfile` / nginx 未 `USER` 降权 |
| **High** | 跨租户数据模型缺失 | 仅 actor 隔离；无组织边界时 SaaS 不可用 |
| **Medium** | 插件动态加载 | 有 allowlist，**无** `PLUGIN_SIGNATURE_CHECK` |
| **Medium** | 默认/示例密钥 | 本地 `.env.docker` 含真实密钥（gitignore，勿提交） |
| **Medium** | CORS / 生产 CSP | 依赖 env；配置错误可放宽跨域 |
| **Medium** | IDOR 残留面 | 依赖 `ensure_task_access` 全覆盖；新资源表需同样过滤 |
| **Low** | CSRF | API Key 头模式为主，浏览器 cookie 会话未用 |
| **Low** | Rate limit | slowapi 可选依赖；需确认生产开启 |

**已有缓解**：API Key 常量时间比较、安全响应头、审计日志、RBAC 装饰器、配额 402、生产 `settings_guard`。

---

## 6. 发布风险

| 风险 | 影响 | 缓解建议 |
|------|------|----------|
| 宣称 SaaS 但无多租户 | 法律/合同与数据隔离不符 | **阻断发布**直至 Tenant 落地 |
| API 无冻结 | 客户端破坏性变更 | OpenAPI 冻结 + CI 兼容检查 |
| 覆盖率低 | 回归漏测 | 分阶段提高到 80% |
| 镜像安全 | 供应链/合规扫描失败 | 非 root + trivy gate |
| 文档与代码漂移 | 交付客诉 | 以 contract + PROJECT_STATUS 为单一事实源 |

**发布门槛建议（Go / No-Go）**：

- [ ] Tenant 隔离测试通过  
- [ ] OpenAPI v1 冻结且兼容检查绿  
- [ ] Critical/High 安全项关闭  
- [ ] Docker 一键 + seed + health 绿  
- [ ] CHANGELOG 打 **v1.0.0**  

---

## 7. 检查清单快照

| 检查项 | 结果 |
|--------|------|
| API 完整性（业务闭环） | ✅ 够用；❌ 缺 tenants/benchmarks |
| 数据库迁移 | ✅ 001–012；需 013+ tenant |
| Docker 构建 | ✅ 本地可构建 |
| 环境变量 | ✅ 有 example；需 profile 三分 |
| 测试覆盖 | ⚠️ 有体量、门禁 35% |
| 安全 | ⚠️ 基础有、企业 hardening 不足 |

---

## 8. 阶段 1→4 落地计划（本提交范围）

| 阶段 | 交付物 |
|------|--------|
| **1 审计** | 本文件 `PROJECT_STATUS.md` |
| **2 API Freeze** | `docs/api-contract.md`, `docs/openapi-v1.json`, export/compat 脚本与测试 |
| **3 Tenant** | 模型 + migration 013 + `TenantContext` + 过滤 + isolation 测试 |
| **4 RBAC** | 企业角色/权限 + 兼容别名 + `docs/rbac-enterprise.md` + 测试 |

**原则**：不改 Evaluation Pipeline 核心；Lite 默认行为保持；新能力模块化开关（`MULTI_TENANT_ENABLED`）。

---

## 9. 评分（审计时点）

| 维度 | 分（/5） |
|------|----------|
| 评测主链路 | 4.5 |
| 企业多租户 | 1.5 → *本阶段升级中* |
| RBAC | 3.5 → *本阶段升级中* |
| Billing | 2.5 |
| Benchmark | 0 |
| 安全 | 3.0 |
| Docker/运维 | 3.5 |
| CI/CD | 3.0 |
| 文档 | 4.0 |
| **总分** | **~3.5 / 5** |

---

*下一阶段（5–12）不在本提交：Billing 产品化、Benchmark、安全扫描闭环、生产 Docker、覆盖率 80%、FINAL_RELEASE_REPORT。*
