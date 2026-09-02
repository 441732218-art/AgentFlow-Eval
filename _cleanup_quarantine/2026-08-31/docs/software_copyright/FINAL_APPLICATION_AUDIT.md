# AgentFlow-Eval V1.0.0 软著最终一致性审核报告

> 审核角色：软件著作权审核
> 审核日期：2026-08
> 审核范围：docs/software_copyright/ 全部材料与 backend/app 真实源码
> 审核性质：只读审核，不修改任何源码

---

## 一、软件基本信息一致性

| 项目 | 结果 | 说明 |
|------|------|------|
| 软件名称一致性 | ✅ | 全材料统一「AgentFlow Intelligence（智能体工作流评测平台）」，仓库名 AgentFlow-Eval |
| 版本一致性 | ✅ | 全材料统一 V1.0.0 |
| 源码一致性 | ✅ | TXT 3385 行；DOCX 60 页 / 3377 段（DOCX 删除说明头 8 行，源码内容一致） |
| 文档一致性 | ✅ | 技术特点、源码清单、用户手册的描述均对应真实源码 |

---

## 二、功能-源码对应审核

| 功能 | 源码位置 | 一致性 |
|------|----------|--------|
| Agent统一执行框架（ReAct执行循环） | `core/agent_runner/openai_runner.py`（`OpenAIReActRunner`） | ✅ |
| 安全工具沙箱（AST白名单求值） | `core/agent_runner/tool_sandbox.py`（`tool_calculator`） | ✅ |
| 混合评分引擎（规则+LLM+降级机制） | `core/judge_engine/llm_judge.py`（`LLMJudge`） | ✅ |
| 动态评分卡（评分维度+权重归一化） | `core/judge_engine/scorecard.py`（`Scorecard`） | ✅ |
| Trace诊断（故障分类+置信度） | `core/diagnosis/engine.py` | ✅ |
| Benchmark分析（compare_runs/finalize_run/leaderboard） | `core/benchmark/service.py` | ✅ |

---

## 三、审核结论

- 软件名称、版本号在各材料中保持一致。
- 六项核心功能均可在真实源码中找到对应实现，未发现功能描述与源码不符的情况。
- 源码提交文件（TXT / DOCX）内容一致，DOCX 删除的 8 行为说明头（标题与首个文件分隔头），非源码内容差异。
- 唯一遗留项为 `tool_sandbox.py` 注释的 mojibake（源文件既有编码问题），非阻断项。

**结论：软著材料一致性通过，可提交。**
