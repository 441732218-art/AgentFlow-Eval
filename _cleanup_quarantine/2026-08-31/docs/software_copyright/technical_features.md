# AgentFlow-Eval 软件著作权技术特点说明（Technical Features）

> 用途：软件著作权申请材料
> 依据：`docs/software_copyright/source_manifest.md` 与 `backend/app/` 真实源码
> 说明：本文所有功能与技术描述均对应真实源码，未虚构功能、未夸大模型能力、未使用商业宣传表述。

---

## 1. 软件主要功能

AgentFlow Intelligence 是一个面向智能体（Agent）工作流的评测平台。软件将任意可调用 Agent 接入统一评测流水线，实现用例执行、轨迹记录、自动评分、对比实验与诊断分析。主要功能包括：

1. **评测任务与用例管理**：创建评测任务、维护测试用例，支持 CSV / JSON 批量导入（`api/v1/endpoints/tasks.py`、`models/test_suite.py`）。
2. **Agent 执行**：内置 ReAct Agent 与外部 HTTP Agent 通过统一契约接入执行（`core/agent_runner/`）。
3. **执行轨迹记录**：记录每次执行的完整步骤（Thought/Action/Observation）、token 消耗、耗时与成本（`models/trace.py`）。
4. **自动评分**：规则指标评分 + 大模型细化评分，支持人工复核覆盖（`core/judge_engine/`、`models/metric_score.py`）。
5. **对比实验**：同一用例集多配置变体并行评测与横向对比（`core/evaluation/compare.py`、`api/v1/endpoints/experiments.py`）。
6. **持续评测**：固定基准用例集 + 回归试跑 + 与基线/上一跑退化检测（`core/benchmark/service.py`）。
7. **诊断分析**：对执行轨迹做启发式根因诊断，输出故障类型、置信度与建议（`core/diagnosis/engine.py`）。
8. **统计实验分析**：对 A/B 实验做显著性检验与样本量计算（`core/ab/stats.py`）。

---

## 2. 软件技术架构

软件采用前后端分离的分层架构：

| 层次 | 技术实现 | 源码位置 |
|------|----------|----------|
| 前端展示层 | Vite + React + Ant Design | `frontend/src/` |
| API 接口层 | FastAPI（REST + WebSocket） | `backend/app/api/v1/` |
| 评测核心层 | 执行框架 / 评分引擎 / 流水线聚合 / 诊断 / 统计 / 持续评测 | `backend/app/core/` |
| 数据持久层 | SQLAlchemy ORM + Alembic 迁移，支持 PostgreSQL / SQLite | `backend/app/models/`、`alembic/` |
| 异步任务层 | Celery / Eager / Memory 三种队列适配（可选 Redis） | `backend/app/core/adapters/queue/`、`core/celery_app/` |

评测核心层内部按职责进一步划分为：

- `core/agent_runner/`：Agent 统一执行框架（抽象基类、OpenAI ReAct 执行器、HTTP 执行器、协议、SSRF 防护、工具沙箱）。
- `core/judge_engine/`：评分引擎（抽象基类、混合评分实现、评分卡模型、规则指标）。
- `core/evaluation/`：流水线聚合与对比的纯函数层。
- `core/diagnosis/`：轨迹诊断分析。
- `core/ab/`：A/B 实验编排与统计检验。
- `core/benchmark/`：持续评测基准服务。

---

## 3. 核心处理流程

评测主流水线由 `core/celery_app/tasks.py` 中的 `run_full_evaluation` 编排，流程如下：

1. **加载任务与用例**：读取评测任务及其测试用例集合。
2. **状态推进**：任务状态由 QUEUED 变更为 RUNNING。
3. **并行执行**：对每个测试用例通过 Celery group 并行调用 `AgentRunner.run()` 执行，结果持久化为 Trace 记录。
4. **并行评分**：对每条 Trace 并行调用 `Judge.evaluate()` 评分，结果持久化为 MetricScore 记录。
5. **聚合汇总**：调用 `core/evaluation/pipeline.py` 中的 `aggregate_pipeline_results()`，计算平均分、各维度平均分、总 token、总耗时，并判定整体状态（completed / partial / failed）。
6. **状态落定**：将任务状态更新为 completed 或 failed。

评分子流程（`core/judge_engine/llm_judge.py` 的 `LLMJudge.evaluate()`）：

1. 规则预评分：依据轨迹步骤计算工具调用准确率、答案文本一致性、推理连贯性等规则分数。
2. 大模型细化（可选）：当配置了 API Key 时，将预评分结果与轨迹一并提交大模型，获取细化后的多维评分。
3. 降级回退：无 API Key、调用超时或出错时，直接采用规则评分结果，保证离线可用。

---

## 4. 主要技术特点

### 4.1 Agent 统一执行框架

软件通过抽象基类 `BaseAgentRunner`（`core/agent_runner/base.py`）定义统一执行契约 `run(query, tools, agent_config)`，所有执行器实现同一接口，由 `build_agent_runner()`（`core/agent_runner/factory.py`）根据任务配置选择具体实现：

- **内置 ReAct 执行器**（`openai_runner.py` 的 `OpenAIReActRunner`）：实现 Thought → Action → Observation → Final Answer 循环，支持函数调用与文本解析两种模式，`_parse_react_steps()` 兼容中英文前缀。
- **外部 HTTP 执行器**（`http_runner.py` 的 `HttpAgentRunner`）：调用用户自有 Agent HTTP 服务，按 `agentflow.http.v1` 协议（`protocol.py`）构造请求并对响应容错归一化。
- **安全防护**：`ssrf.py` 对目标 URL 做 scheme → hostname → IP 字面量 → DNS 解析四层校验，阻断内网/环回/链路本地/云元数据地址；`tool_sandbox.py` 提供受限工具执行。

执行结果统一经 `ensure_pipeline_result()`（`base.py`）归一化为流水线兼容结构，使上层编排无需区分执行器类型。

### 4.2 混合式评测算法

评分引擎 `LLMJudge`（`core/judge_engine/llm_judge.py`）采用"规则 + 大模型"混合评分：

- 规则预评分恒先执行，计算工具调用准确率（`metrics.py` 的 `calc_tool_accuracy()`）、答案一致性、推理连贯性等基础分数。
- 当配置 API Key 时，将规则预评分与轨迹提交大模型进行细化评分（`_build_prompt()`）；无 API Key、超时或出错时自动降级为纯规则评分。
- 词法评分采用字符二元组（`_char_bigrams()`）对中文等 CJK 文本计算字符重叠度，评分结果带缓存（LRU）与软超时控制。

该设计使评分在无外部模型服务时仍可运行，具备离线可用性。

### 4.3 动态评分模型

软件以 `Scorecard` / `ScoreDimension` 模型（`core/judge_engine/scorecard.py`）描述评分维度，支持通过任务配置动态指定：

- 每个维度包含 key、label、权重（weight）、描述与评分方法。
- 权重自动归一化到 100 分（`Scorecard.normalize_weights`），维度 key 唯一性校验。
- 默认评分卡（`default_scorecard()`）定义三维：工具调用准确率（40）、答案准确性（40）、推理连贯性（20）。
- `to_system_prompt()` 根据评分卡动态生成评分提示词；`extract_scorecard_from_agent_config()` 从任务配置中解析自定义评分卡。

### 4.4 Trace 诊断分析

诊断引擎（`core/diagnosis/engine.py`）对执行轨迹做启发式分析：

- `_analyze_trace_steps()` 统计动作数、工具调用、错误信息、循环次数与 token 增长比率，识别死循环（同一工具+参数重复出现）与迭代数过高。
- 归纳五类故障：`agent_loop`、`tool_failure`、`token_drift`、`prompt_drift`、`timeout`，并给出对应置信度（`_confidence()`）、根因描述与改进建议。
- `diagnose_from_traces()` 汇总生成拓扑结构（nodes/edges）与 token/耗时曲线，供前端可视化展示。

### 4.5 Benchmark 持续评测

持续评测服务（`core/benchmark/service.py` 的 `BenchmarkService`）提供固定基准的回归评测：

- 支持创建基准（`create_benchmark()`）、从既有任务克隆用例（`create_from_task()`）、导入用例（CSV/JSON）。
- 运行基准时复用评测引擎生成 `BenchmarkRun`；`finalize_run()` 汇总指标，`leaderboard()` 按标签聚合排行。
- `compare_runs()` 将本次运行与上一跑或指定基线对比平均分、维度分、成功率与覆盖率，判定为 improved / stable / regressed，实现退化检测。

### 4.6 统计实验分析

统计模块（`core/ab/stats.py`）在无第三方统计库依赖下实现显著性检验：

- `welch_t_test()`：方差不等的双样本 Welch t 检验，用于连续指标（评分、延迟）的组间比较。
- 双比例 z 检验：用于转化率/成功率类比例指标的比较，输出 z 统计量、p 值、95% 置信区间与显著性判定。
- `sample_size_proportion()`：依据基线比例、最小可检测效应、显著性水平与统计功效计算每组所需样本量。
- `_norm_ppf()`：逆正态累积分布函数的有理近似实现，供检验与样本量计算使用。

---

## 5. 创新点描述

1. **统一 Agent 接入契约**：以抽象基类统一内置与外部 Agent 的执行接口，配合结果归一化，使不同来源的 Agent 进入同一条评测流水线，避免为不同执行器编写分叉逻辑（`core/agent_runner/base.py`、`factory.py`、`http_runner.py`、`protocol.py`）。

2. **混合式评测算法**：规则评分与可选的模型细化评分相结合，且具备无模型服务时的降级回退能力，兼顾评分质量与离线可用（`core/judge_engine/llm_judge.py`）。

3. **动态评分模型**：评分维度与权重可配置、自动归一化，评分提示词随评分卡动态生成，使评分标准可随评测对象调整（`core/judge_engine/scorecard.py`）。

4. **安全工具沙箱**：采用 AST 白名单方式实现受限算术求值，拒绝名称/函数调用/属性访问/下标访问，避免执行任意代码；工具执行带超时与输出长度限制（`core/agent_runner/tool_sandbox.py`）。

5. **SSRF 多层防护**：对 HTTP Agent 目标地址做 scheme、hostname、IP 字面量与 DNS 解析四层校验，阻断内网与云元数据访问（`core/agent_runner/ssrf.py`）。

6. **启发式 Trace 诊断**：基于轨迹步骤统计归纳故障类型并给出置信度与建议，无需额外模型即可定位 Agent 执行异常（`core/diagnosis/engine.py`）。

7. **自研统计检验**：在无 scipy 依赖下实现 Welch t 检验、双比例 z 检验与样本量计算，支撑 A/B 实验与对比实验的量化判断（`core/ab/stats.py`）。

8. **持续评测与退化检测**：以固定基准集支撑回归评测，通过与基线/历史运行对比实现退化检测（`core/benchmark/service.py`）。

9. **可单测的流水线分层**：将评测聚合与状态判定抽离为无数据库/队列副作用的纯函数，便于单元测试与逻辑复用（`core/evaluation/pipeline.py`）。

---

> 本文描述与真实源码的对应关系详见 `docs/software_copyright/source_manifest.md` 第 2~5 节。

