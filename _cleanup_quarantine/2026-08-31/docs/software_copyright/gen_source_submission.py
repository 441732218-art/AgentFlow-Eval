# -*- coding: utf-8 -*-
"""Generate the software copyright source submission file (60-page plan, section 8).

Reads the ordered core files, prepends a per-file header block, and for
benchmark/service.py extracts only finalize_run / compare_runs / leaderboard.
This script only READS source files; it never modifies or deletes them.
"""
import os

BACKEND = r"d:\AgentFlow-Eval\backend\app"
OUT = r"d:\AgentFlow-Eval\docs\software_copyright\AgentFlow-Eval_V1.0.0_source_code.txt"

# (relative path, 模块功能, 对应创新点) — order follows source_manifest.md section 8
ENTRIES = [
    (r"core\agent_runner\openai_runner.py",
     "内置 ReAct Agent 执行循环内核（Thought→Action→Observation→Final Answer）",
     "Agent 统一执行框架 / ReAct 执行循环"),
    (r"core\agent_runner\tool_sandbox.py",
     "安全工具沙箱（AST 白名单求值，无 eval）",
     "安全工具沙箱"),
    (r"core\agent_runner\base.py",
     "Agent 统一执行契约抽象基类与结果归一化",
     "Agent 统一执行框架"),
    (r"core\agent_runner\factory.py",
     "Agent 执行器工厂（openai / http / plugin 多态选择）",
     "Agent 统一执行框架"),
    (r"core\evaluation\pipeline.py",
     "评测流水线聚合与状态判定纯函数",
     "自动评测 / 可单测流水线分层"),
    (r"core\judge_engine\scorecard.py",
     "可配置评分卡（维度/权重动态定义与归一化）",
     "动态评分模型"),
    (r"core\judge_engine\llm_judge.py",
     "混合式评分引擎（规则 + LLM 细化 + 降级回退）",
     "混合式评测算法"),
    (r"core\diagnosis\engine.py",
     "执行轨迹启发式根因诊断",
     "Trace 诊断分析"),
    (r"models\trace.py",
     "执行轨迹数据模型",
     "Trace 诊断分析（数据层）"),
    (r"core\benchmark\service.py",
     "持续评测退化检测与排行榜（核心段：finalize_run / compare_runs / leaderboard）",
     "Benchmark 持续评测 / 退化检测"),
]

# 1-based inclusive line ranges of the three core methods inside benchmark/service.py
BENCHMARK_SEGMENTS = [
    ("# ===== 核心段 1：finalize_run() =====", 358, 473),
    ("# ===== 核心段 2：compare_runs() =====", 579, 689),
    ("# ===== 核心段 3：leaderboard() =====", 691, 772),
]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read().replace("\r\n", "\n").replace("\r", "\n")


parts = ["AgentFlow-Eval V1.0.0 软件著作权源码提交文件", ""]

for rel, func, innov in ENTRIES:
    full = os.path.join(BACKEND, rel)
    parts.append("================================")
    parts.append("文件路径：" + rel)
    parts.append("模块功能：" + func)
    parts.append("对应创新点：" + innov)
    parts.append("================================")
    parts.append("")

    if rel == r"core\benchmark\service.py":
        lines = read_text(full).split("\n")
        parts.append("# ===== 类上下文：class BenchmarkService（节选核心方法）=====")
        parts.append("# 注：方法依赖的 import（select/selectinload、BenchmarkRun、NotFoundError 等）与模块级辅助函数 _now() 见原文件顶部。")
        parts.append("class BenchmarkService:")
        for note, start, end in BENCHMARK_SEGMENTS:
            parts.append("    " + note)
            parts.extend(lines[start - 1:end])
            parts.append("")
    else:
        parts.append(read_text(full).rstrip("\n"))
        parts.append("")

with open(OUT, "w", encoding="utf-8-sig") as f:
    f.write("\n".join(parts))

print("DONE:", OUT)
print("total lines:", len(parts))
