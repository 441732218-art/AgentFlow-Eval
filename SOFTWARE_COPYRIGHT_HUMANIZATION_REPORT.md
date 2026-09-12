# AgentFlow-Eval V1.0.0 第二阶段人工化整理报告

**整理日期：** 2026-09-13
**阶段：** 第二阶段（P0 + P1）
**原则：** 仅注释 / docstring / 格式 / 空行 / 模板化说明；不改业务逻辑

---

## 1. 修改文件列表（9 文件）

| 文件 | 变更量 | 主要改动 |
|------|--------|----------|
| `backend/app/core/agent_runner/tool_sandbox.py` | −55 / +24 | P0 分隔符删除、空行；注释/docstring 中文化 |
| `backend/app/core/agent_runner/base.py` | −25 | 去 Sphinx 式 docstring，中文业务说明 |
| `backend/app/core/agent_runner/factory.py` | −8 | docstring/注释压缩 |
| `backend/app/core/agent_runner/openai_runner.py` | −8 | class/method docstring、注释人工化 |
| `backend/app/core/evaluation/pipeline.py` | −4 | 模块 docstring、partition 说明 |
| `backend/app/core/judge_engine/scorecard.py` | −12 | 删模板注释、无效 elif/pass 块 |
| `backend/app/core/judge_engine/llm_judge.py` | −20 | 注释/docstring 中文化，删 LRU 教程注释 |
| `backend/app/core/diagnosis/engine.py` | −4 | 模块/函数 docstring、拓扑注释 |
| `backend/app/core/benchmark/service.py` | −4 | finalize/compare docstring 与行内注释 |

**未修改：** `models/trace.py`（按约定保留 v1.0 分区注释）

**两阶段合计（9 文件 scoped diff）：** `84 insertions(+), 311 deletions(-)`

---

## 2. P0 执行项

| 项 | 文件 | 状态 |
|----|------|------|
| 删除 `# ---` 装饰分隔符 | `tool_sandbox.py` L27–29 | ✅ |
| `tool_retrieve_simulate` 与 `tool_json_get` 之间补空行 | `tool_sandbox.py` L175 | ✅ |
| 删除无效 `# always pass...` + `elif: pass` | `scorecard.py` L166–168 | ✅ |

---

## 3. P1 执行项（按文件）

### `tool_sandbox.py`
- `ToolSandboxError` docstring → 中文短句
- 行内注释改为中文工程口吻（插件 hook、stub、去重、fn 挂载等）

### `base.py`
- 模块/类/方法 docstring 去掉 `:meth:` / `:class:` 交叉引用
- `# Duck-typed fallback` → `# 兼容旧对象/测试替身`

### `factory.py`
- docstring 一行化；插件注释缩短

### `openai_runner.py`
- `OpenAIReActRunner` / `OpenAIRunner` docstring 人工化
- 代理、AOLS、ReAct 相关注释压缩
- **未改** ReAct 主循环体、Prompt、error_msg

### `pipeline.py`
- 模块 docstring 一行中文
- `partition_suite_results` 说明中文化

### `scorecard.py`
- 删 `One scoring dimension` 空 docstring
- `# Weights...` / `# Module-level singleton` / `# Nested forms` 模板注释
- `default_scorecard` docstring 中文化

### `llm_judge.py`
- 删 Re-export / Fallback prompt / CJK 学术注释
- `_pre_score` / `_llm_refine` / `_heuristic_coherence_score` docstring 中文化
- 删 LRU「Move to end」等教程注释
- **未改** `SYSTEM_PROMPT`、`_build_prompt`、评分算法

### `diagnosis/engine.py`
- 模块 docstring 去 `AI-style` 措辞
- `diagnose_from_traces` docstring 中文化
- **未改** `_suggestion()` 中文诊断文案

### `benchmark/service.py`
- `finalize_run` / `compare_runs` docstring 中文化
- 行内注释去 Verdict/Highlight 英文章节标题

---

## 4. 明确未执行项（按用户限制）

| 限制 | 遵守 |
|------|------|
| 不修改函数签名 | ✅ |
| 不修改类结构 | ✅ |
| 不修改 import | ✅ |
| 不修改算法逻辑 | ✅ |
| 不修改 Prompt | ✅ |
| 不修改 ReAct 主循环 | ✅ |
| 不提取 `_REACT_PREFIXES` | ✅ |
| 不合并 try/except observability | ✅ |
| 不新增业务抽象函数 | ✅ |

---

## 5. Git 验证

### `git diff --stat`（9 文件）

```
 backend/app/core/agent_runner/base.py          | 50 +++-------------
 backend/app/core/agent_runner/factory.py       | 42 +------------
 backend/app/core/agent_runner/openai_runner.py | 23 +++-----
 backend/app/core/agent_runner/tool_sandbox.py  | 79 +++++++++----------------
 backend/app/core/benchmark/service.py          | 12 ++--
 backend/app/core/diagnosis/engine.py           | 10 ++--
 backend/app/core/evaluation/pipeline.py        | 77 +++---------------------
 backend/app/core/judge_engine/llm_judge.py     | 82 +++++---------------------
 backend/app/core/judge_engine/scorecard.py     | 20 ++-----
 9 files changed, 84 insertions(+), 311 deletions(-)
```

### `git diff --check`

- **结果：** exit code 2
- **原因：** `tool_sandbox.py`、`diagnosis/engine.py` 等文件为 **CRLF** 行尾，`git diff --check` 报告 trailing whitespace（Windows 换行符特征，非本次引入的逻辑问题）
- **逻辑扫描：** scoped diff 中无新增 `import` / `def` / `class` / 算法行变更（除第一阶段已删除的未引用 `_web_search` 死代码）

### 业务行为一致性

| 维度 | 结论 |
|------|------|
| ReAct 循环 | 未改动函数体 |
| Tool Sandbox AST | 未改动 |
| LLM Judge 评分 | 未改动 |
| Prompt 文本 | 未改动 |
| Benchmark 计算 | 未改动 |
| Trace 模型 | 未改动 |
| `scorecard.extract_judge_config` | 删除仅含 `pass` 的 `elif` 分支，返回值不变 |

**结论：与 V1.0.0 业务行为保持一致。**

---

## 6. 软著 PDF 导出建议

1. 从当前 9+1（trace 未动）核心文件 UTF-8 快照导出
2. 不要插入 `==== 创新点 ====` 模板块
3. 优先使用已人工化的中文注释版本

---

## 7. 关联文档

- 第一阶段：`SOFTWARE_COPYRIGHT_CLEANUP_REPORT.md`
- 冻结审查：V1.0.0 Software Copyright Freeze Report（对话记录）
