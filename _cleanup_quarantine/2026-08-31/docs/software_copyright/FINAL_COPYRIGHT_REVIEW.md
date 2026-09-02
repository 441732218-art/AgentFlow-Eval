# AgentFlow-Eval 软件著作权源码提交前最终审查报告

> 审查对象：`docs/software_copyright/AgentFlow-Eval_V1.0.0_source_code.txt`
> 审查性质：只读检查，不修改任何源码
> 审查日期：2026-08
> 软件名称：AgentFlow Intelligence（智能体工作流评测平台）· 版本 V1.0.0

---

## 〇、审查结论摘要

| 检查项 | 结果 |
|--------|------|
| 敏感信息（password/secret/api_key/token/private key） | ✅ 未发现硬编码密钥 |
| eval( / exec( / 第三方版权声明 | ✅ 无内置 `eval()`（旧 `_calculator` 已删除）；无 `exec`；无第三方版权声明 |
| 文件顺序与 source_manifest.md 第 8 节一致 | ✅ 完全一致（10 文件顺序正确） |
| 截断函数 / 缺失 class 上下文 / 不完整代码块 | ✅ class 上下文已补充；无函数截断；仍存在源文件既有乱码 |

**总体结论：结构正确、无敏感信息泄露、顺序一致、class 上下文已补充、无内置 eval，可提交；仅存 1 项建议在正式提交前人工复核的非阻断问题（源文件既有乱码，非本次生成引入）。**

---

## 1. 审查范围与方法

- 对象：软著源码提交文件（3385 行，UTF-8 with BOM）。
- 方法：对全文做关键字扫描（大小写不敏感），并与 `source_manifest.md` 第 8 节最终 60 页方案逐项比对。

## 2. 敏感信息检查（✅ 通过）

扫描 `password / secret / api_key / token / private key`，全部命中均为**变量名、参数名或环境变量引用**，未发现任何硬编码的密钥/口令/私钥：

- `api_key: str | None = None`（函数参数）
- `os.environ.get("OPENAI_API_KEY", "")`（从环境变量读取，非明文）
- `max_tokens / total_tokens / prompt_tokens / completion_tokens / token_cost`（Token 计量字段）
- `"Check OPENAI_API_KEY, HTTPS_PROXY, and OPENAI_BASE_URL in .env"`（错误提示文案）

**结论：无敏感信息泄露。**

## 3. 危险函数与第三方版权检查（✅ 通过）

| 检查项 | 结果 | 位置 |
|--------|------|------|
| `exec(` | ✅ 无 | — |
| 第三方版权声明（Copyright / MIT / Apache / BSD / GPL 等） | ✅ 无 | — |
| 内置 `eval(` | ✅ 无（旧 `_calculator` 已删除） | — |

**说明：**

- 提交文件第 797~824 行的 `_eval(node)` 是 AST 白名单求值器 `tool_calculator` 内部的**递归辅助函数**（函数名含 `_eval`，非 Python 内置 `eval`），安全无虞。
- 原旧版 `_calculator()` 中的内置 `eval(expression, allowed_names)` 已在本次提交前删除，现仅保留 AST 白名单版本 `tool_calculator()` 及其内部 `_eval()`。

## 4. 文件顺序一致性检查（✅ 通过）

提交文件中的 10 个「文件路径：」分隔头顺序如下，与 `source_manifest.md` 第 8 节最终方案**完全一致**：

```
core\agent_runner\openai_runner.py
core\agent_runner\tool_sandbox.py
core\agent_runner\base.py
core\agent_runner\factory.py
core\evaluation\pipeline.py
core\judge_engine\scorecard.py
core\judge_engine\llm_judge.py
core\diagnosis\engine.py
models\trace.py
core\benchmark\service.py
```

## 5. 代码完整性检查（⚠️ 1 项需关注）

### 5.1 无函数截断（✅）
benchmark/service.py 三个核心段均完整，未出现函数中途截断：

- `finalize_run()`：以 `scored_count += 1` 完整收尾
- `compare_runs()`：以 `}` 完整收尾
- `leaderboard()`：以 `return board` 完整收尾（文件末尾）

### 5.2 缺失 class 上下文（✅ 已解决）
本次已通过 `gen_source_submission.py` 在 benchmark 核心段前补充 `class BenchmarkService:` 声明与依赖说明，三个方法现处于正确的类上下文内。方法依赖的外部符号（`select` / `selectinload`、`BenchmarkRun`、`NotFoundError`、`AgentFlowError`、`TestSuite`、模块级辅助函数 `_now()` 等）已在补注的「类上下文」注释中列明。

### 5.3 源文件既有乱码（⚠️）
`tool_sandbox.py` 的 `tool_time_query()` 函数注释与文档字符串存在 **mojibake（乱码）**，例如：

```
涓轰粈涔堣?鍗曠嫭瀹炵幇杩欎釜宸?叿鑰屼笉鏄??鐢?current_datetime
```

该乱码**为源文件 `tool_sandbox.py` 既有编码问题（UTF-8 被误按 GBK 解读后残留），并非本次生成引入**——生成脚本以 UTF-8 读取/写入，忠实保留了源文件原貌。

**建议（需人工授权）：修正源文件 `tool_sandbox.py` 中 `tool_time_query`、`_web_search`、`_calculator` 等处的乱码注释后重新生成；本次不修改源码。**

## 6. 问题清单（按优先级）

| 级别 | 问题 | 位置 | 处理建议 |
|------|------|------|----------|
| 低 | 源文件注释乱码（mojibake） | `tool_sandbox.py` `tool_time_query` 等 | 修正源文件后重新生成 |

## 7. 审查结论

该源码提交文件**结构完整、顺序正确、无敏感信息、无第三方版权内容、无函数截断**，符合软著提交的基本要求。

上述 1 项问题为**非阻断**项，源于**源文件既有情况**（源文件乱码），非本次生成过程引入。建议在正式提交前由人工确认并处理，处理方式均不涉及本次审查范围（只检查、不修改源码）。
