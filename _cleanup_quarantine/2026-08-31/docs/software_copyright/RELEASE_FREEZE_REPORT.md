# RELEASE_FREEZE_REPORT — 软著源码提交版本冻结报告

> 冻结日期：2026-08
> 软件名称：AgentFlow Intelligence（智能体工作流评测平台）
> 版本号：V1.0.0
> 冻结范围：软件著作权源码提交版本

---

## 1. 最终源码提交文件

| 项目 | 内容 |
|------|------|
| 提交文件 | `docs/software_copyright/AgentFlow-Eval_V1.0.0_source_code.txt` |
| 编码 | UTF-8 with BOM |
| 总行数 | **3385 行** |

---

## 2. 最终包含文件列表（10 个，按提交顺序）

| 顺序 | 闭环阶段 | 文件路径 | 行数 |
|------|----------|----------|------|
| 1 | ① Agent执行 | `core/agent_runner/openai_runner.py` | 730 |
| 2 | ① Agent执行 | `core/agent_runner/tool_sandbox.py` | 570 |
| 3 | ② 统一接入 | `core/agent_runner/base.py` | 108 |
| 4 | ② 统一接入 | `core/agent_runner/factory.py` | 114 |
| 5 | ③ 评测流水线 | `core/evaluation/pipeline.py` | 203 |
| 6 | ④ 评分模型 | `core/judge_engine/scorecard.py` | 173 |
| 7 | ④ 评分模型 | `core/judge_engine/llm_judge.py` | 589 |
| 8 | ⑤ Trace诊断 | `core/diagnosis/engine.py` | 379 |
| 9 | ⑤ Trace诊断 | `models/trace.py` | 133 |
| 10 | ⑥ Benchmark优化 | `core/benchmark/service.py`（核心段） | 309 |

> 说明：第 10 项 `benchmark/service.py` 仅提交核心段 `finalize_run()` / `compare_runs()` / `leaderboard()`，并以 `class BenchmarkService:` 上下文包裹。

---

## 3. 最终源码行数

| 项目 | 行数 |
|------|------|
| 源码内容（10 文件，不含分隔头） | **3308 行** |
| 分隔头 / 说明 / 类上下文注释 | 77 行 |
| 提交文件总行数 | **3385 行** |

> 页数估算（按 50 行/页）：源码内容约 66 页；正式提交按软著「前 30 页 + 后 30 页」规则截取。详细页序见 `source_manifest.md` 第 8 节。

---

## 4. 已处理风险

| # | 风险项 | 处理结果 |
|---|--------|----------|
| 1 | benchmark 核心段缺失 `class BenchmarkService` 上下文 | ✅ 已补充类声明与依赖说明，方法处于正确类上下文内 |
| 2 | 旧版 `_calculator()` 使用内置 `eval()` | ✅ 已删除旧实现，仅保留 AST 白名单版 `tool_calculator()` 与内部 `_eval()` |

---

## 5. 未处理低风险

| # | 风险项 | 位置 | 说明 |
|---|--------|------|------|
| 1 | 注释乱码（mojibake） | `tool_sandbox.py` 的 `tool_time_query` / `_web_search` 等 | 源文件既有编码问题（UTF-8 被误按 GBK 解读后残留），非本次生成引入，不影响功能 |

---

## 6. 最近一次测试结果

| 测试范围 | 结果 |
|----------|------|
| `tests/unit/test_tool_sandbox.py` | ✅ 7 passed |
| `tests/unit/test_openai_runner.py` + `tests/unit/test_tool_sandbox.py` | ✅ **13 passed, 0 failed** |
| 运行环境 | Python 3.12.10 · pytest 8.3.3 |

---

## 7. 冻结声明

**本软件著作权源码提交版本（V1.0.0）自本报告之日起冻结，不再修改任何业务源码。**

- 提交文件 `AgentFlow-Eval_V1.0.0_source_code.txt` 为最终交付版本。
- 相关软著材料（`source_manifest.md`、`technical_features.md`、`FINAL_COPYRIGHT_REVIEW.md`）与本报告构成完整交付链。
- 除已列明的「未处理低风险（mojibake 注释）」外，其余审查项均通过。
