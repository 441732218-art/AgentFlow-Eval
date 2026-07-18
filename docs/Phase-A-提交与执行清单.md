# Phase A — 提交拆分与执行清单

| 属性 | 内容 |
|------|------|
| **来源** | [项目全面审查报告.md](./项目全面审查报告.md) §11 Phase A |
| **目标** | 真相源统一与演示硬化；把本地 Unreleased 有序落库 |
| **建议版本** | 发布后打 tag **`v0.2.0`**（Intelligence + AOLS + 企业扩展） |
| **日期** | 2026-07-18 |
| **原则** | 按主题拆 commit/PR；每批可测、可回滚；先基建与后端，后前端与文档 |

> **执行前请确认：** 当前 `main` 上有大量未提交改动。本清单**不自动 git commit/push**（除非你明确要求）。可按下列批次用 `git add` 选择性暂存。

---

## 0. 总览：建议提交批次

| 批次 | 主题 | 建议 commit message（中文 Conventional） | 风险 | 状态 |
|------|------|------------------------------------------|------|------|
| **C0** | 清理噪音 | `chore: ignore temp files and tighten env secret patterns` | 低 | ✅ `ddb3161` |
| **C1** | 开源元文件 | `docs: add CONTRIBUTING, SECURITY, changelog, and issue templates` | 低 | ✅ `c384f6e` |
| **C2** | 后端核心评测扩展 | `feat(backend): experiments, http runner, pipeline, resilience, and cache` | 中 | ✅ `e57bd3d` |
| **C3** | 企业横切 | `feat(backend): me api, observability kpis, slow tasks, and production guards` | 中 | ✅ `aff564f` |
| **C4** | 多模态 / AB / 插件 / 计费 | `feat(backend): multimodal, ab tests, plugins, and billing skeleton` | 中 | ✅ `710af59` |
| **C5** | Intelligence API | `feat(backend): dashboard, diagnosis, and aols agent_logs` | 中 | ✅ `1a62673` |
| **C6** | 测试与场景 | `test(backend): unit coverage for enterprise and aols` | 低 | 🔶 已并入 C2–C5 各批测试；可跳过或仅补漏 |
| **C7** | 前端 Command Center | `feat(frontend): intelligence center, auth shell, and brand assets` | 中 | ✅ `7f2a345`（含 C8/C9，因壳层耦合） |
| **C8** | 前端运营页与权限 | （并入 C7） | 中 | ✅ 并入 `7f2a345` |
| **C9** | 品牌与静态资源 | （并入 C7） | 低 | ✅ 并入 `7f2a345` |
| **C10** | 部署脚本与 compose | `feat(deploy): lite profile, verify scripts, and docker examples` | 中 | ✅ `2d9aa45` |
| **C11** | 文档中心 | `docs: intelligence review, module map, and feature guides` | 低 | 🔶 本批提交中 |
| **C12** | 版本发布 | `chore(release): v0.2.0 intelligence center` | 低 | ⬜ |

可将 C2–C5 合并为更大 PR，但**不建议**单次「全部 add .」一个巨型 commit。

---

## 1. 批次明细（路径级）

### C0 — 清理噪音

**做：**

- 确认 `.gitignore` 含：`.env*` 密钥、`__pycache__`、`node_modules`、`*.db`（若不应入库）、Office 锁 `~$*`、临时 `tmp*.txt`
- 删除或移出工作区：`tmp2_timestamps.txt`、`scripts/~$nerate_source_deposit_pdf.py` 等

**不要提交：**

- `backend/agentflow_eval.db`、真实 `.env`、`logs/*.log`、本机密钥

---

### C1 — 开源元文件

| 路径（示例） |
|--------------|
| `CHANGELOG.md`、`CONTRIBUTING.md`、`SECURITY.md` |
| `.github/ISSUE_TEMPLATE/`、`.github/PULL_REQUEST_TEMPLATE.md` |
| 视情况：`.github/workflows/*` 的合理改动 |

---

### C2 — 后端：评测扩展与工程层

| 路径（示例） |
|--------------|
| `backend/app/core/evaluation/` |
| `backend/app/core/agent_runner/factory.py`、`http_runner.py` 及 runner 改动 |
| `backend/app/core/resilience/`、`cache/`、`db/`、`ports/`、`adapters/`、`profiles/` |
| `backend/app/api/v1/endpoints/experiments.py`、`schemas/experiment.py`、`models/experiment.py` |
| `backend/alembic/versions/006_*.py`、`007_*.py` |
| 相关 `requirements.txt`、`config.py` 片段 |

**自测：** `pytest tests/unit/test_pipeline.py tests/unit/test_http_runner.py tests/unit/test_resilience.py tests/unit/test_cache_layer.py -q`

---

### C3 — 后端：RBAC / 可观测 KPI

| 路径（示例） |
|--------------|
| `backend/app/core/rbac.py`、`settings_guard.py`、`cli/` |
| `backend/app/api/v1/endpoints/me.py`、`observability.py` |
| `backend/app/core/observability/`（**暂不含**完整 aols 亦可并入 C5） |
| `backend/app/models/slow_task.py`、`011_slow_task_events.py` |

**自测：** `pytest tests/unit/test_rbac.py tests/unit/test_me_api.py tests/unit/test_observability_api.py tests/unit/test_slow_tasks_persist.py -q`

---

### C4 — 后端：多模态 / A/B / 插件 / 计费

| 路径（示例） |
|--------------|
| `backend/app/core/multimodal/`、`ab/`、`plugins/`、`billing/` |
| `backend/app/api/v1/endpoints/{media,ab,plugins,billing}.py` |
| `backend/app/models/{media_asset,ab_test,billing}.py` |
| `backend/app/plugins/examples/` |
| migrations `008`–`010` |

**自测：**  
`pytest tests/unit/test_multimodal.py tests/unit/test_ab_*.py tests/unit/test_plugins.py tests/unit/test_billing*.py tests/unit/test_stripe_checkout.py -q`

---

### C5 — 后端：Dashboard / Diagnosis / AOLS

| 路径（示例） |
|--------------|
| `backend/app/api/v1/endpoints/{dashboard,diagnosis,logs}.py` |
| `backend/app/core/diagnosis/` |
| `backend/app/core/observability/aols/`、`timeseries.py` 等 |
| `backend/app/models/agent_log.py`、`012_agent_logs.py` |
| `backend/app/utils/logger.py`、middleware 日志相关改动 |

**自测：**  
`pytest tests/unit/test_diagnosis.py tests/unit/test_aols_*.py tests/unit/test_logs_api.py tests/unit/test_timeseries.py -q`

---

### C6 — 后端测试与场景全量

| 路径 |
|------|
| `backend/tests/unit/` 全部新增 |
| `backend/tests/scenarios/` |
| `backend/tests/conftest.py` 等改动 |

**自测：** `pytest tests/unit/ tests/scenarios/ -q`（全绿再提交）

---

### C7 — 前端：Intelligence Center

| 路径（示例） |
|--------------|
| `frontend/src/dashboard/`、`traces/`、`diagnosis/`、`analytics/`、`monitoring/` |
| `frontend/src/theme/`、`styles/command-center.css`、`styles/theme.css` |
| `frontend/src/components/charts/`、`flow/`、`widgets/`、`common/PageShell.tsx` |
| `frontend/src/router/index.tsx`、`components/layout/*`、`navItems.tsx` |
| `frontend/package.json`（echarts 等依赖） |

**自测：** `cd frontend; npm run type-check; npm run build`

---

### C8 — 前端：运营、权限、API

| 路径（示例） |
|--------------|
| `frontend/src/auth/` |
| `frontend/src/pages/billing/`、`pages/plugins/` |
| `frontend/src/api/endpoints/{dashboard,diagnosis,logs,billing,plugins,observability}.ts` |
| `frontend/src/hooks/use{Dashboard,Diagnosis,Logs,Billing,Observability}*.ts` |
| 任务/报告页与 MainLayout 联调改动 |

**自测：** 同上 + `npm test`

---

### C9 — 品牌

| 路径 |
|------|
| `docs/brand/` |
| `frontend/public/assets/`、`frontend/public/brand/`、`frontend/public/favicon.svg` |
| `frontend/src/components/brand/` |
| README 中 logo 引用（可放 C11） |

---

### C10 — 部署与脚本

| 路径 |
|------|
| `scripts/start-lite.ps1`、`demo-playbook.ps1`、`post-deploy-verify.ps1`、`generate-deploy-env.ps1` 等 |
| `backend/docker-compose*.yml`、`.env.*.example` |
| `docs/deploy-profiles.md`、`DEMO.md`、`production-checklist.md`（或并入 C11） |
| `deploy.env.example`、`railway.json`、`vercel.json` 合理改动 |

**自测：** Lite 启动健康检查；或 `post-deploy-verify`（若环境具备）

---

### C11 — 文档中心

| 路径 |
|------|
| `docs/项目全面审查报告.md` |
| `docs/Phase-A-提交与执行清单.md`（本文） |
| `docs/功能模块清单.md`、`docs/项目报告.md`、`docs/README.md` |
| 专题：`observability*.md`、`rbac.md`、`billing.md`、`plugins.md` 等 |
| 根 `README.md` 产品叙事更新 |

---

### C12 — 发布

1. 将 `CHANGELOG.md` 中 `[Unreleased]` 折叠为 `## [0.2.0] - YYYY-MM-DD`
2. 视需要 bump `frontend/package.json` version → `0.2.0`
3. Tag：`git tag -a v0.2.0 -m "AgentFlow Intelligence v0.2.0"`
4. **仅在你明确要求后** push 分支与 tag

---

## 2. Phase A 功能执行清单（相对「仅提交」的额外工作）

审查报告 Phase A 五项；**提交代码 alone ≠ Phase A 完成**。

| ID | 工作项 | 状态 | 建议动作 |
|----|--------|------|----------|
| **A1** | 提交与版本 | 🔶 进行中（C0–C5 + 前端 C7–C9 已落库） | 按 C0–C12 落库；发 `v0.2.0` |
| **A2** | 文档同步 | ✅ 部分完成 | 模块清单 + 全面审查报告已更新；发布后刷新 CHANGELOG 日期 |
| **A3** | 空态与 seed | ⬜ 待办 | 检查 `seed.py` 是否覆盖 Dashboard/Diagnosis 演示字段；统一 EmptyState 文案 |
| **A4** | 日志驱动面板 MVP | ⬜ 待办 | Dashboard 或 Monitoring 至少 1–2 卡片直接读 `GET /logs/statistics` 或 event 计数 |
| **A5** | Command Center E2E | ⬜ 待办 | Playwright：访问 `/dashboard` `/traces` `/diagnosis` `/analytics` `/monitoring` 冒烟 |

### A3 验收检查

```text
[ ] python -m app.core.seed 后 /dashboard 核心卡片非全空
[ ] /diagnosis 在存在失败 trace 时给出非 healthy 主因（或明确 healthy）
[ ] 无数据时各 Command 页 EmptyState 一致、无白屏
```

### A4 验收检查（实现提示）

```text
[ ] Monitoring 页：已接 /logs（基线）
[ ] Dashboard：新增「近 24h 事件数 / 错误事件」等 1 张卡片 ← 读 agent_logs 统计
[ ] 跑一轮评测后卡片数字变化
```

### A5 验收检查

```text
[ ] frontend/e2e/ 增加 command-center.spec.ts（或等价）
[ ] CI 或本地 npx playwright test 通过
```

---

## 3. 推荐执行顺序（一天版 / 三天版）

### 紧凑（1 天，仅落库）

1. C0 清理 → C1 元文件  
2. C2+C3+C4+C5 后端（可 1–2 个 commit）→ C6 测试  
3. C7+C8 前端 → C9 品牌  
4. C10 部署 → C11 文档  
5. 全量 `pytest` + `npm run build`  
6. C12 本地 tag（暂不 push）

### 完整 Phase A（2–3 天）

1. 同上落库至 C11  
2. 实现 **A3 seed/空态** 小 PR  
3. 实现 **A4 日志卡片** 小 PR  
4. 实现 **A5 Playwright** 小 PR  
5. C12 发布说明 + tag +（可选）push / 开 PR

---

## 4. 每批提交前命令模板（PowerShell）

```powershell
# 后端
cd D:\AgentFlow-Eval\backend
# 激活 venv 后：
pytest tests/unit/ -q --tb=no

# 前端
cd D:\AgentFlow-Eval\frontend
npm run type-check
npm run build
```

选择性暂存示例（勿直接复制全路径，按批次调整）：

```powershell
cd D:\AgentFlow-Eval
git status -sb
git add CHANGELOG.md CONTRIBUTING.md SECURITY.md .github/
git commit -m "docs: add CONTRIBUTING, SECURITY, changelog, issue templates"
```

---

## 5. 风险与注意

| 项 | 说明 |
|----|------|
| 密钥 | 永远不要 `git add backend/.env` 或含真实 `OPENAI_API_KEY` 的文件 |
| 数据库文件 | 本地 SQLite 一般不入库 |
| 巨型 commit | 审查/回滚困难；至少前后端与文档分开 |
| origin/main | 远程仍停在旧 tip；推送前与协作者确认 |
| 软著材料 | `docs/soft-copyright/generated/` 体量大，可单独 commit 或保持本地产物 |

---

## 6. 完成定义（Definition of Done）

Phase A **完成**当且仅当：

- [ ] C0–C11 代码已在版本库（本地 main 或 PR 分支）  
- [ ] `pytest tests/unit/` 与前端 build 通过  
- [ ] A3 / A4 / A5 验收勾选完成  
- [ ] CHANGELOG 出现 `0.2.0` 发布节  
- [ ] （可选）`v0.2.0` tag；远程同步策略已明确  

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-18 | 首版：提交批次 C0–C12 + Phase A 功能项 A1–A5 |
