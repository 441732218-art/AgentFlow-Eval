# AgentFlow-Eval V1.0.0 Soft Copyright Freeze Audit

**审计日期：** 2026-09-13
**审计类型：** 只读冻结前终审
**当前分支：** `main`
**审计结论：** **条件通过 — 可冻结 V1.0.0 核心源码，但必须隔离导出，不可使用全仓库工作区快照**

---

## 1. 十文件存在性检查

| # | 文件路径 | 存在 | V1 能力 |
|---|----------|------|---------|
| 1 | `backend/app/core/agent_runner/openai_runner.py` | ✅ | Agent Runner (ReAct) |
| 2 | `backend/app/core/agent_runner/tool_sandbox.py` | ✅ | Tool Sandbox |
| 3 | `backend/app/core/agent_runner/base.py` | ✅ | Runner 统一契约 |
| 4 | `backend/app/core/agent_runner/factory.py` | ✅ | Runner 工厂 |
| 5 | `backend/app/core/evaluation/pipeline.py` | ✅ | Evaluation Pipeline |
| 6 | `backend/app/core/judge_engine/scorecard.py` | ✅ | 动态评分卡 |
| 7 | `backend/app/core/judge_engine/llm_judge.py` | ✅ | LLM Judge |
| 8 | `backend/app/core/diagnosis/engine.py` | ✅ | Diagnosis |
| 9 | `backend/app/models/trace.py` | ✅ | Trace 数据模型 |
| 10 | `backend/app/core/benchmark/service.py` | ✅ | Benchmark |

**结果：** 10/10 文件均存在，路径有效。

---

## 2. 核心符号检查

### 2.1 Agent Runner

| 符号 | 文件 | 状态 |
|------|------|------|
| `OpenAIReActRunner` | `openai_runner.py` | ✅ |
| `REACT_SYSTEM_PROMPT` | `openai_runner.py` | ✅ |
| `OpenAIRunner` (legacy) | `openai_runner.py` | ✅ |
| `BaseAgentRunner` | `base.py` | ✅ |
| `AgentResult` | `base.py` | ✅ |
| `ensure_pipeline_result` | `base.py` | ✅ |
| `build_agent_runner` | `factory.py` | ✅ |

### 2.2 Tool Sandbox

| 符号 | 文件 | 状态 |
|------|------|------|
| `run_tool_sandboxed` | `tool_sandbox.py` | ✅ |
| `BUILTIN_TOOLS` | `tool_sandbox.py` | ✅ |
| `tool_time_query` | `tool_sandbox.py` | ✅ |
| AST `tool_calculator` / `_eval` | `tool_sandbox.py` | ✅ |

### 2.3 Evaluation Pipeline

| 符号 | 文件 | 状态 |
|------|------|------|
| `map_agent_status_to_trace` | `pipeline.py` | ✅ |
| `aggregate_pipeline_results` | `pipeline.py` | ✅ |
| `determine_overall_status` | `pipeline.py` | ✅ |
| `partition_suite_results` | `pipeline.py` | ✅ |

### 2.4 LLM Judge / Scorecard

| 符号 | 文件 | 状态 |
|------|------|------|
| `Scorecard` / `ScoreDimension` | `scorecard.py` | ✅ |
| `default_scorecard` | `scorecard.py` | ✅ |
| `LLMJudge.evaluate` | `llm_judge.py` | ✅ |
| `LLMJudge._pre_score` | `llm_judge.py` | ✅ |
| `LLMJudge._llm_refine` | `llm_judge.py` | ✅ |

### 2.5 Diagnosis

| 符号 | 文件 | 状态 |
|------|------|------|
| `diagnose_from_traces` | `engine.py` | ✅ |
| `diagnose_task` | `engine.py` | ✅ |
| `ISSUE_*` 常量集 | `engine.py` | ✅ |
| 中文 `_suggestion()` | `engine.py` | ✅ |

### 2.6 Trace / Benchmark

| 符号 | 文件 | 状态 |
|------|------|------|
| `Trace` / `TraceStatus` | `trace.py` | ✅ |
| `BenchmarkService.finalize_run` | `service.py` | ✅ |
| `BenchmarkService.compare_runs` | `service.py` | ✅ |
| `BenchmarkService.leaderboard` | `service.py` | ✅ |

**结果：** 全部核心符号存在，V1.0.0 功能链完整。

---

## 3. V2 Runtime / 实验代码混入检查

### 3.1 十文件内部依赖扫描

对 10 个核心文件扫描 `from app.runtime` / `business_agents` / `agent_evaluation` / `workflow` / `core.runtime`：

| 文件 | V2/实验 import | 标记 (`A5-`, `v2.3`, `business_agents`) |
|------|----------------|----------------------------------------|
| 全部 10 文件 | **0 处** | **0 处** |

**结论：** 十文件源码本身 **无 V2 runtime 代码混入**，符合 V1.0.0 软著范围。

### 3.2 工作区整体（非十文件）

| 区域 | 状态 | 风险 |
|------|------|------|
| `backend/app/runtime/**` | 大量 M + 新增 untracked | 🔴 全仓库导出会混入 V2 |
| `backend/app/workflow/**` | 大量 A (staged/new) | 🔴 非 V1 范围 |
| `backend/app/business_agents/**` | untracked | 🔴 非 V1 范围 |
| `backend/app/agent_evaluation/**` | untracked | 🔴 非 V1 范围 |
| `backend/app/core/runtime/**` | D (deleted) | 🟡 V2 迁移痕迹 |
| `README.md` | M，含 V2 API 描述 | 🔴 软著材料勿用 |
| `docs/v2.*` | untracked | 🔴 非 V1 范围 |

**结论：** 仓库工作区 **整体 ≠ V1.0.0**；仅 **十文件子集** 可代表 V1 提交源码。

---

## 4. 十文件 Git 变更状态

### 4.1 相对 HEAD 的修改

| 文件 | 工作区变更 | 变更性质（经前三阶段审计） |
|------|------------|---------------------------|
| `openai_runner.py` | M | 注释/docstring 人工化 |
| `tool_sandbox.py` | M | 注释/docstring + CRLF→LF + 死代码删除 |
| `base.py` | M | 注释/docstring |
| `factory.py` | M | 注释/docstring |
| `pipeline.py` | M | 注释/docstring |
| `scorecard.py` | M | 注释/docstring |
| `llm_judge.py` | M | 注释/docstring |
| `engine.py` | M | 注释/docstring + CRLF→LF |
| `service.py` | M | 注释/docstring |
| `trace.py` | **无变更** | 与 HEAD 一致 ✅ |

### 4.2 diff 统计

**含行尾变更：**
```
9 files changed, 976 insertions(+), 1203 deletions(-)
```

**忽略行尾后（`--ignore-cr-at-eol`）：**
```
9 files changed, 84 insertions(+), 311 deletions(-)
```

→ 大量 +/- 来自 `tool_sandbox.py` / `engine.py` 的 CRLF→LF；**语义 diff 仅为展示层整理**。

### 4.3 `git diff --check`（十文件）

```
exit code: 0  ✅ 无 trailing whitespace 告警
```

### 4.4 业务逻辑不变确认

- 十文件 scoped diff 扫描：**无**新增/修改函数体、签名、import、算法行
- `trace.py`：**零 diff**，可作为 V1 基线参照
- 关联报告：
  - `SOFTWARE_COPYRIGHT_CLEANUP_REPORT.md`
  - `SOFTWARE_COPYRIGHT_HUMANIZATION_REPORT.md`
  - `SOFTWARE_COPYRIGHT_FORMAT_FIX_REPORT.md`

---

## 5. Git 工作区总览

```
分支：main
已修改 (M)：~60+ 文件（含 V2 runtime、main.py、router、tests、frontend）
已删除 (D)：backend/app/core/runtime/** 等
未跟踪 (??)：business_agents、agent_evaluation、governance、workflow、docs/v2.* 等
已暂存 (A)：backend/app/workflow/** 大量新文件
未提交报告：SOFTWARE_COPYRIGHT_*.md（3 份）
```

**关键风险：** 当前 `main` 工作区是 **V1 软著整理 + V2 开发混合态**，未 commit、未 tag。

---

## 6. 风险项

| 等级 | 风险 | 说明 | 缓解 |
|------|------|------|------|
| 🔴 P0 | 全仓库导出/PDF | 工作区含 V2 runtime/workflow/business_agents | **仅导出 10 文件清单** |
| 🔴 P0 | 无 V1 冻结 tag/commit | 9 文件变更未提交，无法 reproducible 冻结 | 建 `softcopyright-v1.0.0` tag |
| 🟡 P1 | README 含 V2 内容 | `ENABLE_RUNTIME_V2`、business API | 软著材料不含 README |
| 🟡 P1 | `openai_runner.py` 有未提交 diff | 仅注释层，但需纳入冻结 commit | 与 9 文件一并提交 |
| 🟢 P2 | diff stat 行数偏大 | CRLF→LF 造成 | 用 `--ignore-cr-at-eol` 验证 |
| 🟢 P2 | `trace.py` 未动 | 无风险，反而可作对照 | 冻结时保留 HEAD 版本 |

---

## 7. 最终冻结建议

### ✅ 可以冻结

**条件：** 以 **10 个核心文件** 为唯一源程序范围，不包含工作区其他路径。

推荐冻结清单（按 PDF 页序）：

1. `backend/app/core/agent_runner/openai_runner.py`
2. `backend/app/core/agent_runner/tool_sandbox.py`
3. `backend/app/core/agent_runner/base.py`
4. `backend/app/core/agent_runner/factory.py`
5. `backend/app/core/evaluation/pipeline.py`
6. `backend/app/core/judge_engine/scorecard.py`
7. `backend/app/core/judge_engine/llm_judge.py`
8. `backend/app/core/diagnosis/engine.py`
9. `backend/app/models/trace.py`
10. `backend/app/core/benchmark/service.py`

### 📋 冻结操作步骤（建议）

1. **创建隔离快照**（仅 10 文件）：
   ```bash
   git stash push -m "v2-wip" -- $(git diff --name-only | grep -v '^backend/app/core/\|^backend/app/models/trace')
   # 或：单独 checkout 10 文件到临时目录
   ```

2. **提交 V1 软著整理**（9 文件 + 可选 3 份 REPORT）：
   ```bash
   git add <10-file-list> SOFTWARE_COPYRIGHT_*.md
   git commit -m "chore(softcopyright): freeze V1.0.0 core source presentation layer"
   git tag -a softcopyright-v1.0.0 -m "AgentFlow-Eval V1.0.0 软著源程序冻结"
   ```

3. **从 tag 导出 PDF**：
   - UTF-8 直接排版
   - **禁止**插入 `==== 创新点 ====` 模板块
   - 不要附带 README / runtime / workflow 目录

4. **导出前再验**：
   ```bash
   git diff --check -- <10-file-list>   # 必须为 0
   ```

### ❌ 不可冻结（当前工作区）

- 整个 `D:/AgentFlow-Eval` 工作区快照
- `README.md`（含 V2 描述）
- `backend/app/runtime/**`、`workflow/**`、`business_agents/**`
- 任何 untracked V2.1/V2.2/V2.3 文档与模块

---

## 8. 审计结论

| 维度 | 结果 |
|------|------|
| 十文件存在性 | ✅ 通过 |
| 核心符号 | ✅ 通过 |
| 十文件无 V2 混入 | ✅ 通过 |
| 十文件无实验标记 | ✅ 通过 |
| 十文件格式检查 | ✅ `git diff --check` 通过 |
| 工作区整体纯净度 | ❌ 不通过（V2 混合） |
| **综合冻结判定** | **✅ 条件通过 — 十文件子集可冻结** |

---

**审计人：** Agent（只读审计，未修改代码）
**下一步：** 按 §7 创建 `softcopyright-v1.0.0` tag 并从该 tag 导出最终 PDF。
