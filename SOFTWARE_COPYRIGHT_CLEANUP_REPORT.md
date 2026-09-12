# AgentFlow-Eval V1.0.0 软著源码整理报告

**整理日期：** 2026-09-13
**整理类型：** 展示层人工化（注释 / docstring / 乱码修复 / 死代码删除）
**原则：** 不修改任何业务逻辑、接口签名、运行时 Prompt

---

## 1. 修改文件列表

| 文件 | 变更行数（约） | 变更类型 |
|------|----------------|----------|
| `backend/app/core/agent_runner/base.py` | −24 | docstring 压缩、删除 Phase 0 |
| `backend/app/core/agent_runner/factory.py` | −30 | 删除页眉、压缩 docstring |
| `backend/app/core/agent_runner/tool_sandbox.py` | −40 / +25 | 页眉、乱码、死代码 |
| `backend/app/core/evaluation/pipeline.py` | −55 | Args/Returns 压缩 |
| `backend/app/core/judge_engine/scorecard.py` | −4 | 删除 Phase 3 |
| `backend/app/core/judge_engine/llm_judge.py` | −45 | Architecture/Features/Args 压缩 |
| `backend/app/core/benchmark/service.py` | −1 | 删除 Phase 3/4 注释 |

**合计（上述 7 文件）：** 40 insertions, 220 deletions（`git diff --stat`）

---

## 2. 修改内容明细

### P0 — 全部执行

#### `tool_sandbox.py`
- 删除重复页眉 `# AgentFlow-Eval Agent自动化评测工作台 V1.0`
- 修复 `tool_time_query` 参数行格式（`**kwargs` 换行）及 `# noqa` 中文注释乱码
- 修复 `tool_time_query` / `tool_retrieve_simulate` docstring 乱码，压缩为 3–4 行，**保留 2026-04 踩坑说明**
- 修复行内中文注释乱码（未知格式回退、top_k 限制、假文档生成）
- 修复 `BUILTIN_TOOLS.retrieve_simulate` 参数 description 乱码
- 修复截断后缀：`"... [truncated]"`（原 mojibake）
- 删除未引用死代码：重复 `logger = ...`、`_web_search` stub 及分隔注释块

#### `factory.py`
- 删除重复页眉

#### `benchmark/service.py`
- 行内注释删除 `(Phase 3/4)`

### 指定项

#### `base.py`
- 模块 docstring 删除 `(Phase 0)`，压缩说明
- `ensure_pipeline_result`、`BaseAgentRunner.run` 删除 Args/Returns 模板

#### `pipeline.py`
- 7 个纯函数的 Google Style Args/Returns 压缩为 1 行说明

#### `scorecard.py`
- 模块 docstring 删除 `(Phase 3)`，保留默认 40/40/20 说明

#### `factory.py`（docstring）
- 删除内嵌 JSON 示例与 Args/Returns，保留 runner 类型与协议文档引用

#### `llm_judge.py`
- 模块 docstring：删除 `Architecture:` 三段式，改为简短中文说明
- 类 docstring：删除 `Features:` 列表
- `__init__` / `evaluate` / `tokenize` / `_lexical_answer_score`：压缩 Args/Returns

---

## 3. 未修改项（按约定保留）

| 类别 | 说明 |
|------|------|
| 其他文件页眉 | `config.py`、`router.py` 等 ~8 个文件的重复页眉**未动** |
| `models/trace.py` | `# ---- v1.0 新增 ----` 分区注释**未动** |
| `diagnosis/engine.py` | 中文诊断建议文案**未动** |
| `openai_runner.py` | `error_msg` 编号清单**未动** |
| 运行时 Prompt | `REACT_SYSTEM_PROMPT`、`to_system_prompt()`、`_build_prompt` 等**未动** |

---

## 4. 未修改核心模块（逻辑完整保留）

- **Agent Runner：** ReAct 循环、function calling、proxy、AOLS 埋点
- **Tool Sandbox：** AST 白名单求值、超时截断、插件 hook、工具注册表
- **Evaluation Pipeline：** 状态映射、聚合、partition 逻辑
- **Scorecard：** Pydantic 权重归一化、默认维度
- **LLM Judge：** 规则预评分、LLM refine、降级、LRU cache、CJK bigram
- **Benchmark Service：** finalize_run / compare_runs / leaderboard 算法

---

## 5. 逻辑未变化说明

`git diff`（仅上述 7 文件）验证结果：

- **无**函数体算法变更
- **无**类结构、变量名、接口签名变更
- **无** ORM 字段、数据库模型变更
- **无** ReAct / Sandbox / Judge / Benchmark 计算逻辑变更

### 运行时字符串说明（语义等价修复）

以下变更仅修复 mojibake 或死代码删除，不改变程序分支与算法：

| 位置 | 变更 | 影响 |
|------|------|------|
| `tool_time_query` logger 文案 | 乱码 → 可读中文 | 日志文本可读性 |
| `run_tool_sandboxed` 截断后缀 | 乱码 → `"... [truncated]"` | 超长工具输出后缀 |
| `retrieve_simulate` schema description | 乱码 → 正确中文 | OpenAI tool 参数描述 |
| `_web_search` stub | 删除（未被引用） | 无运行时影响 |

---

## 6. Git 验证命令

```bash
git diff --stat -- \
  backend/app/core/agent_runner/base.py \
  backend/app/core/agent_runner/tool_sandbox.py \
  backend/app/core/agent_runner/factory.py \
  backend/app/core/evaluation/pipeline.py \
  backend/app/core/judge_engine/scorecard.py \
  backend/app/core/judge_engine/llm_judge.py \
  backend/app/core/benchmark/service.py
```

**结果：** `7 files changed, 40 insertions(+), 220 deletions(-)`

完整 diff 仅含注释、docstring、乱码修复与死代码删除，**无业务代码逻辑 diff**。

---

## 7. 后续建议（软著 PDF 导出）

源码中不存在 PDF 里的 `==== 文件路径 / 模块功能 / 对应创新点 ====` 块；若重新导出 PDF，请**不要**再插入该模板层，直接从整理后的 UTF-8 源码生成即可。
