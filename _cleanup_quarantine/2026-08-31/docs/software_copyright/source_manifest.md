# AgentFlow-Eval 软件著作权源码清单（Source Manifest）

> 本文档用于软件著作权申请材料整理，记录核心源码的归属、作用与核心算法位置。
> 仅作材料整理用途，不修改、不删除、不重构任何源代码或目录结构。

---

## 1. 软件基本信息

| 项目 | 内容 |
|------|------|
| 软件名称 | AgentFlow Intelligence（智能体工作流评测平台） |
| 仓库名称 | AgentFlow-Eval |
| 版本号 | V1.0.0 |
| 软件类型 | 应用软件 / 平台软件 |
| 开发语言 | 后端 Python 3.11+（FastAPI / SQLAlchemy / Celery）；前端 React 18（TypeScript） |
| 软件简称 | AgentFlow-Eval |

---

## 2. 核心源码列表（13 个文件）

> 路径均相对 `backend/app/`。行数按 2026-08 基线统计。

| # | 文件路径 | 行数 | 累计行数 | 文件作用 | 核心算法位置 |
|---|----------|------|----------|----------|--------------|
| 1 | `core/agent_runner/openai_runner.py` | 663 | 663 | 内置 ReAct Agent 执行循环内核 | `OpenAIReActRunner.run()`、`_parse_react_steps()`、`ReActStep` |
| 2 | `core/judge_engine/llm_judge.py` | 525 | 1188 | 混合式 LLM-as-Judge 评分引擎 | `LLMJudge.evaluate()`、`_heuristic_coherence_score()`、`_char_bigrams()`、`_build_prompt()` |
| 3 | `core/evaluation/pipeline.py` | 162 | 1350 | 评测流水线聚合纯函数（无 DB/Celery 副作用） | `aggregate_pipeline_results()`、`partition_suite_results()`、`determine_overall_status()` |
| 4 | `core/judge_engine/scorecard.py` | 145 | 1495 | 可配置评分卡（维度/权重归一化） | `Scorecard`、`default_scorecard()`、`extract_scorecard_from_agent_config()` |
| 5 | `core/agent_runner/tool_sandbox.py` | 509 | 2004 | 安全工具沙箱（AST 白名单求值） | `tool_calculator()`、`run_tool_sandboxed()`、`resolve_tools_for_suite()` |
| 6 | `core/agent_runner/http_runner.py` | 252 | 2256 | 外部 HTTP Agent 接入与响应归一化 | `HttpAgentRunner.run()`、`_normalize_response()` |
| 7 | `core/agent_runner/protocol.py` | 192 | 2448 | 统一接入协议 `agentflow.http.v1` | `HttpAgentRequestV1/ResponseV1/StepV1`、`coerce_http_response()` |
| 8 | `core/diagnosis/engine.py` | 341 | 2789 | 启发式根因诊断引擎 | `_analyze_trace_steps()`、`diagnose_from_traces()`、`diagnose_task()` |
| 9 | `core/benchmark/service.py` | 728 | 3517 | 持续评测：基准/跑分/退化检测 | `BenchmarkService.finalize_run()`、`compare_runs()`、`leaderboard()` |
| 10 | `core/ab/stats.py` | 294 | 3811 | 自研显著性检验（无 scipy） | `welch_t_test()`、双比例 z 检验、`sample_size_proportion()`、`_norm_ppf()` |
| 11 | `core/judge_engine/metrics.py` | 54 | 3865 | 规则指标计算 | `calc_tool_accuracy()`、`extract_answer_text()` |
| 12 | `models/trace.py` | 117 | 3982 | 执行轨迹数据模型 | `Trace`、`TraceStatus` |
| 13 | `models/metric_score.py` | 83 | 4065 | 评分指标持久化模型 | `MetricScore`、`effective_score` |

**文件总行数：4065 行（13 个文件）**

---

## 3. 文件作用详述

### 3.1 执行内核
- **`openai_runner.py`**：实现 `Thought → Action → Observation → Final Answer` 的 ReAct 循环；支持 function-calling 与文本解析两种模式；含 `ReActStep` 数据结构、token 统计与异常安全降级。
- **`tool_sandbox.py`**：内置工具注册与沙箱执行；`tool_calculator()` 采用 AST 白名单求值（禁止 Name/Call/Attribute/Subscript），杜绝任意代码执行；线程池超时、输出长度限制。
- **`http_runner.py`**：把用户自有的外部 HTTP Agent 服务接入同一评测管线，并对响应做归一化。
- **`protocol.py`**：定义 `agentflow.http.v1` 协议请求/响应数据模型，提供响应容错强转工具。

### 3.2 评分与评测算法
- **`llm_judge.py`**：混合评分引擎——规则预评分恒跑 → 有 API Key 时 LLM 细化 → 无 Key/超时/报错自动降级纯规则；CJK 感知词法评分、LRU 结果缓存、软超时。
- **`scorecard.py`**：可配置评分卡，Pydantic 建模评分维度/权重，自动归一化到 100 分，动态生成评测系统提示词（默认三维 40/40/20）。
- **`metrics.py`**：规则指标工具函数（工具调用准确率、答案抽取、文本归一化）。
- **`pipeline.py`**：流水线聚合与状态机纯函数，负责结果归一化、成功/失败分拣、多维度聚合。

### 3.3 分析与统计
- **`ab/stats.py`**：不依赖 scipy 自研 Welch t 检验、双比例 z 检验、逆正态 CDF 有理近似、样本量计算。
- **`diagnosis/engine.py`**：从 Trace 步骤启发式识别 agent_loop / tool_failure / token_drift / prompt_drift / timeout 五类故障，附置信度、根因与建议。
- **`benchmark/service.py`**：持续评测闭环——基准创建、用例导入、调用评测引擎、排行榜聚合与退化检测（improved / stable / regressed）。

### 3.4 数据模型
- **`trace.py`**：Trace 执行轨迹模型，保存完整 ReAct steps、token 分拆、成本与版本追踪字段。
- **`metric_score.py`**：MetricScore 评分持久化模型，支持 LLM 置信度与人工审核覆盖。

---

## 4. 核心算法位置（函数级）

| 核心算法 | 文件 | 关键类 / 函数 |
|----------|------|---------------|
| ReAct 执行循环 | `openai_runner.py` | `OpenAIReActRunner.run()`、`_parse_react_steps()`、`ReActStep` |
| 混合评分引擎 | `llm_judge.py` | `LLMJudge.evaluate()`、`_heuristic_coherence_score()`、`_char_bigrams()`、`_build_prompt()`、`_analyze_steps()` |
| 评分卡权重归一化 | `scorecard.py` | `Scorecard`（`normalize_weights`）、`default_scorecard()` |
| 规则指标计算 | `metrics.py` | `calc_tool_accuracy()`、`extract_answer_text()` |
| 安全算术求值（AST 白名单） | `tool_sandbox.py` | `tool_calculator()`、内部 `_eval()` |
| HTTP 协议适配 | `http_runner.py` / `protocol.py` | `HttpAgentRunner.run()`、`coerce_http_response()`、`build_http_request_payload()` |
| 流水线聚合 | `evaluation/pipeline.py` | `aggregate_pipeline_results()`、`partition_suite_results()`、`determine_overall_status()`、`normalize_judge_result()` |
| 显著性检验 | `ab/stats.py` | `welch_t_test()`、双比例 z 检验、`sample_size_proportion()`、`_norm_ppf()` |
| 根因诊断 | `diagnosis/engine.py` | `_analyze_trace_steps()`、`diagnose_from_traces()`、`diagnose_task()`、`_confidence()` |
| 退化检测 / 排行榜 | `benchmark/service.py` | `finalize_run()`、`compare_runs()`、`leaderboard()` |

---

## 5. 软著创新点映射

| # | 创新点 | 对应源码位置 |
|---|--------|--------------|
| 1 | 统一 Agent 接入契约（内置 ReAct 与外部 HTTP Agent 同管线） | `openai_runner.py`、`http_runner.py`、`protocol.py` |
| 2 | 混合式 LLM-as-Judge（规则 + LLM + 降级回退） | `llm_judge.py` |
| 3 | 可配置评分卡（维度/权重动态定义与归一化） | `scorecard.py` |
| 4 | 安全工具沙箱（AST 白名单，无 eval） | `tool_sandbox.py` |
| 5 | 多变体对比 + 自研显著性检验（无 scipy） | `ab/stats.py`、`evaluation/pipeline.py` |
| 6 | 持续评测退化检测 | `benchmark/service.py` |
| 7 | 启发式根因诊断（含置信度） | `diagnosis/engine.py` |
| 8 | 可单测的纯函数评测流水线分层 | `evaluation/pipeline.py` |
| 9 | 评分持久化 + 人工复核覆盖 | `models/metric_score.py` |

---

## 6. 推荐提交顺序（60 页 ≈ 3000 行规划）

> 软著标准：前 30 页 + 后 30 页 = 60 页，每页 ≥50 行。13 文件合计 4065 行 ≈ 81 页，超出 60 页，需按"前 30 页取最前 1500 行 + 后 30 页取最后 1500 行"取舍中间约 1065 行。

### 前 30 页（第 1~30 页，约 1495 行）——算法内核

| 顺序 | 文件 | 行数 | 累计 | 对应页 |
|------|------|------|------|--------|
| 1 | `core/agent_runner/openai_runner.py` | 663 | 663 | 第 1~13 页 |
| 2 | `core/judge_engine/llm_judge.py` | 525 | 1188 | 第 14~23 页 |
| 3 | `core/judge_engine/scorecard.py` | 145 | 1333 | 第 24~27 页 |
| 4 | `core/evaluation/pipeline.py` | 162 | 1495 | 第 28~30 页 |

### 后 30 页（第 31~60 页，约 1450 行）——工程闭环支撑

| 顺序 | 文件 | 行数 | 累计 | 对应页 |
|------|------|------|------|--------|
| 5 | `core/agent_runner/tool_sandbox.py` | 509 | 509 | 第 31~40 页 |
| 6 | `core/diagnosis/engine.py` | 341 | 850 | 第 41~47 页 |
| 7 | `core/ab/stats.py` | 294 | 1144 | 第 48~53 页 |
| 8 | `core/agent_runner/http_runner.py` | 252 | 1396 | 第 54~58 页 |
| 9 | `core/judge_engine/metrics.py` | 54 | 1450 | 第 59~60 页 |

**提交合计 ≈ 2945 行 ≈ 59 页。**

### 不提交（因 60 页上限跳过，约 1120 行）

| 文件 | 行数 | 跳过理由 |
|------|------|----------|
| `core/benchmark/service.py` | 728 | 含较多 CRUD 样板，退化检测核心逻辑可后续单独抽取后提交 |
| `core/agent_runner/protocol.py` | 192 | 以 Pydantic 数据模型定义为主 |
| `models/trace.py` | 117 | SQLAlchemy 数据模型定义，样板为主 |
| `models/metric_score.py` | 83 | SQLAlchemy 数据模型定义，样板为主 |

> 说明：若希望保留退化检测创新点，可用 `benchmark/service.py` 替换后 30 页中的 `http_runner.py` + `metrics.py`。

---

## 7. 提交注意事项

1. 文件头已带 `# AgentFlow-Eval Agent自动化评测工作台 V1.0` 注释，提交前统一为 **V1.0.0**。
2. 源码按上述顺序整文件连续提交，不跳行、不删注释（中文注释是自主开发佐证）。
3. 前 30 页与后 30 页必须为同一软件版本、顺序连续。
4. 不建议提交 `tests/`、`__init__.py`、`config.py`、构建产物与第三方依赖。

---

## 8. 最终60页源码提交版本

> 按软件著作权审核逻辑重新排序：以「完整业务闭环」为主线组织文件，而非按代码量排序。
> 闭环主线：**Agent执行 → 统一接入 → 评测流水线 → 评分模型 → Trace诊断 → Benchmark优化**。

### 8.1 文件顺序与页数估算

#### 前 30 页（第 1~30 页，约 1515 行）—— 阶段 ①~③

| 阶段 | 顺序 | 文件路径 | 行数 | 对应页 |
|------|------|----------|------|--------|
| ① Agent执行 | 1 | `core/agent_runner/openai_runner.py` | 663 | 第 1~13 页 |
| ① Agent执行 | 2 | `core/agent_runner/tool_sandbox.py` | 509 | 第 14~23 页 |
| ② 统一接入 | 3 | `core/agent_runner/base.py` | 88 | 第 24~25 页 |
| ② 统一接入 | 4 | `core/agent_runner/factory.py` | 93 | 第 26~27 页 |
| ③ 评测流水线 | 5 | `core/evaluation/pipeline.py` | 162 | 第 28~30 页 |

#### 后 30 页（第 31~60 页，约 1428 行）—— 阶段 ④~⑥

| 阶段 | 顺序 | 文件路径 | 行数 | 对应页 |
|------|------|----------|------|--------|
| ④ 评分模型 | 6 | `core/judge_engine/scorecard.py` | 145 | 第 31~33 页 |
| ④ 评分模型 | 7 | `core/judge_engine/llm_judge.py` | 525 | 第 34~43 页 |
| ⑤ Trace诊断 | 8 | `core/diagnosis/engine.py` | 341 | 第 44~50 页 |
| ⑤ Trace诊断 | 9 | `models/trace.py` | 117 | 第 51~52 页 |
| ⑥ Benchmark优化 | 10 | `core/benchmark/service.py`（核心段） | ~300 | 第 53~60 页 |

**提交合计：10 个文件 ≈ 2943 行 ≈ 59 页。**

> 说明：`benchmark/service.py` 提交其核心段 `finalize_run()` / `compare_runs()` / `leaderboard()`（约 300 行），其余 CRUD（`create_benchmark` / `add_cases` / import）不提交。

### 8.2 保留理由（按闭环主线）

| 阶段 | 保留文件 | 保留理由 |
|------|----------|----------|
| ① Agent执行 | `openai_runner.py`、`tool_sandbox.py` | ReAct 执行循环内核 + AST 白名单工具沙箱，是「执行」环节的独创性核心，放最前供评审第一时间看到 |
| ② 统一接入 | `base.py`、`factory.py` | 统一执行契约与工厂多态，代码虽短但体现「统一接入」的架构设计，承上启下 |
| ③ 评测流水线 | `pipeline.py` | 聚合与状态判定的纯函数层，体现可单测的分层设计，是流水线逻辑的浓缩 |
| ④ 评分模型 | `scorecard.py`、`llm_judge.py` | 动态评分卡 + 混合评分引擎，是「评分模型」的算法核心，直接体现评测能力 |
| ⑤ Trace诊断 | `diagnosis/engine.py`、`models/trace.py` | 根因诊断引擎 + 轨迹数据模型，构成「Trace诊断」闭环 |
| ⑥ Benchmark优化 | `benchmark/service.py`（核心段） | 退化检测（`compare_runs`/`finalize_run`）+ 排行榜（`leaderboard`），是「Benchmark优化」闭环的关键算法 |

### 8.3 删除 / 压缩 / 备选理由（未进入主 60 页的文件）

| 类别 | 文件 | 行数 | 理由 |
|------|------|------|------|
| 备选 | `core/ab/stats.py` | 294 | 自研显著性检验（Welch t / 双比例 z），算法价值高；因「⑥ Benchmark优化」已由 `benchmark/service.py` 核心段承担，暂列为备选，如需突出统计实验可换入 |
| 备选 | `core/evaluation/compare.py` | 83 | 多变体横向对比辅助，其比较功能已被 `benchmark/service.py` 的 `compare_runs` 覆盖，列为备选 |
| 压缩 | `core/agent_runner/http_runner.py` | 252 | 网络调用与异常处理样板为主；「统一接入」已由 `base.py` + `factory.py` 体现，HTTP 接入细节可在技术特点中文字说明 |
| 压缩 | `core/agent_runner/protocol.py` | 192 | 以 Pydantic 请求/响应数据模型定义为主，样板性质 |
| 压缩 | `core/agent_runner/ssrf.py` | 165 | 安全加固逻辑，代码密度较低，可在技术特点中体现 |
| 压缩 | `core/celery_app/tasks.py` | 811 | 编排含大量埋点/事件样板，核心聚合已浓缩在 `pipeline.py` |
| 删除 | `core/judge_engine/base.py` | 32 | 抽象接口占位，无算法实现 |
| 删除 | `core/judge_engine/metrics.py` | 54 | 规则指标辅助函数，已被 `llm_judge.py` 引用 |
| 删除 | `models/metric_score.py` | 83 | SQLAlchemy 数据模型样板 |
| 删除 | `core/observability/tracing.py` | 44 | TraceID 上下文样板，非评测核心 |

> **最终结论**：`benchmark/service.py` 纳入核心提交（后 30 页「⑥ Benchmark优化」核心段）；`ab/stats.py`、`evaluation/compare.py` 列为备选，不进入主 60 页。

---

## 9. 软著审核阅读路径

> 从审核人员阅读角度，说明源码为何按当前顺序提交，使前、后 30 页形成一条可读的技术叙事主线。

### 9.1 五步阅读主线

审核人员按顺序翻阅源码，依次看到如下五步，逐步建立对软件能力的完整认知：

**第 1 步 · Agent执行（第 1~27 页）**
`openai_runner.py` → `tool_sandbox.py` → `base.py` → `factory.py`
- 先看到 ReAct 执行循环内核，理解"软件如何驱动 Agent 执行任务"；再看工具沙箱，理解"执行中如何安全调用工具"；最后以统一契约（`base.py` / `factory.py`）收口，说明内置与外部 Agent 被同一接口接管。
- 放最前的原因：执行是评测的起点、独创性最强，评审在前几页即可确认"这是具备真实执行内核的评测平台"。

**第 2 步 · 自动评测（第 28~30 页）**
`pipeline.py`
- 说明单个执行结果如何被聚合为整体评测结果（平均分、维度分、token、耗时与整体状态判定）。
- 承接执行、引出评分，是"自动评测"编排逻辑的浓缩。

**第 3 步 · 评分模型（第 31~43 页）**
`scorecard.py` → `llm_judge.py`
- 说明"如何对每条执行轨迹打分"：动态评分卡定义维度/权重，混合评分引擎执行规则 + 模型细化 + 降级回退。
- 评分是评测的核心，置于流水线之后、诊断之前，逻辑顺承。

**第 4 步 · Trace诊断（第 44~52 页）**
`diagnosis/engine.py` → `models/trace.py`
- 说明"如何从执行轨迹定位故障"：五类故障归纳、置信度、根因与建议；轨迹模型交代数据来源。
- 评分之后自然进入"分析失败原因"的环节。

**第 5 步 · Benchmark优化（第 53~60 页）**
`ab/stats.py` → `evaluation/compare.py`
- 说明"如何用统计检验量化不同版本/配置的优劣"，支撑持续优化与退化检测。
- 收尾于"优化闭环"，与开头"执行"呼应，使软件"执行 → 评测 → 优化"的完整能力得以呈现。

### 9.2 顺序设计的核心理由（审核视角）

1. **先"执行"后"评测"**：先证明"能跑起来"，再证明"能评得准"，符合阅读与理解的认知顺序。
2. **高密度算法前置**：ReAct 内核、AST 沙箱、混合评分引擎分别落在前/后 30 页的关键位置，保证评审在每一段都能读到算法密度高的文件。
3. **闭环收口**：末段落在"对比/优化"，使评审读完后形成完整闭环认知，而非零散的功能罗列。

### 9.3 重新评估：tool_sandbox.py 与 benchmark/service.py

**`tool_sandbox.py` —— 结论：保留为核心提交文件（维持前 30 页第 2 位）**

- 保留理由：`tool_calculator()` 采用 AST 白名单求值（拒绝名称/调用/属性/下标访问），是"无 eval 的安全工具执行"这一差异化能力的最直接证据，属于"Agent执行"环节的必要支撑。
- 风险与建议（本次不修改）：文件内模拟工具（`web_search` 返回模拟结果、`current_datetime` 等）与 observability 埋点占比偏高；若后续需压缩行数，可优先精简这些样板，但应保留 `tool_calculator` + `run_tool_sandboxed` 核心。
- 已处理：旧版 `_calculator()`（使用内置 eval）与新版 AST 实现重复的问题，已在提交前删除旧实现，现仅保留 AST 白名单版本 `tool_calculator()` 与内部 `_eval()`。

**`benchmark/service.py` —— 结论：应由"压缩"提升为核心提交文件**

- 升级理由：`compare_runs()` / `finalize_run()` 实现的退化检测（improved / stable / regressed）正是"Benchmark优化"闭环的关键算法，是"持续评测"能力的直接证据；第 8.3 节将其列为"压缩"低估了其创新价值。
- 落地建议：将其纳入后 30 页「⑥ Benchmark优化」环节，抽取时优先保留 `finalize_run()`、`compare_runs()`、`leaderboard()` 三个核心方法；其余 CRUD（`create_benchmark` / `add_cases` / import）可精简。

### 9.4 最终 60 页建议（已在第 8 节落地）

- 前 30 页维持不变：Agent执行 → 统一接入 → 评测流水线。
- 后 30 页「⑥ Benchmark优化」由 `benchmark/service.py`（核心段，约 300 行）替代 `ab/stats.py` + `evaluation/compare.py`（合计 377 行）；`ab/stats.py`、`evaluation/compare.py` 均列为备选。
- 总量仍控制在约 60 页（约 3000 行）内，通过精简 `tool_sandbox.py` 样板与 `benchmark/service.py` 的 CRUD 部分实现。




