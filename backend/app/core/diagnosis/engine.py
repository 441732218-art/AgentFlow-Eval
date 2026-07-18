# (c) 2026 AgentFlow-Eval
"""Failure diagnosis engine — heuristic AI-style root-cause analysis for tasks/traces."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.models.test_suite import TestSuite
from app.models.trace import Trace


ISSUE_AGENT_LOOP = "agent_loop"
ISSUE_TOOL_FAILURE = "tool_failure"
ISSUE_TOKEN_DRIFT = "token_drift"
ISSUE_PROMPT_DRIFT = "prompt_drift"
ISSUE_TIMEOUT = "timeout"
ISSUE_NONE = "healthy"


def _step_type(step: dict[str, Any]) -> str:
    return str(step.get("type") or step.get("role") or "").lower()


def _analyze_trace_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Heuristic analysis of a single trace's ReAct steps."""
    steps = steps or []
    action_count = 0
    tool_names: list[str] = []
    observations: list[str] = []
    errors: list[str] = []
    tokens_series: list[int] = []
    loop_pairs: list[tuple[str, str]] = []

    prev_tool = ""
    prev_input = ""
    for step in steps:
        st = _step_type(step)
        content = str(step.get("content") or step.get("observation") or "")
        tool = str(step.get("tool_name") or step.get("action") or "")
        tool_input = str(step.get("tool_input") or step.get("action_input") or "")
        tok = int(step.get("tokens") or 0)
        if tok:
            tokens_series.append(tok)

        if st in {"action", "tool"} or tool:
            action_count += 1
            if tool:
                tool_names.append(tool)
            if tool and tool_input:
                pair = (tool, tool_input[:120])
                loop_pairs.append(pair)
                if prev_tool == tool and prev_input == tool_input[:120]:
                    pass  # counted later via Counter
                prev_tool, prev_input = tool, tool_input[:120]

        if st in {"observation", "tool_result"} or content:
            observations.append(content[:500])
            low = content.lower()
            if any(
                k in low
                for k in (
                    "error",
                    "exception",
                    "timeout",
                    "failed",
                    "traceback",
                    "rate limit",
                    "429",
                    "5xx",
                )
            ):
                errors.append(content[:300])

    pair_counts = Counter(loop_pairs)
    max_loop = max(pair_counts.values()) if pair_counts else 0
    loop_detected = max_loop >= 2 or action_count >= 6

    token_growth = 0.0
    if len(tokens_series) >= 2 and tokens_series[0] > 0:
        token_growth = (tokens_series[-1] - tokens_series[0]) / max(tokens_series[0], 1)

    return {
        "action_count": action_count,
        "tool_names": tool_names,
        "errors": errors,
        "loop_detected": loop_detected,
        "loop_count": max_loop if loop_detected else 0,
        "token_series": tokens_series,
        "token_growth_ratio": round(token_growth, 4),
        "step_count": len(steps),
    }


def _confidence(issue: str) -> float:
    return {
        ISSUE_AGENT_LOOP: 0.86,
        ISSUE_TOOL_FAILURE: 0.9,
        ISSUE_TOKEN_DRIFT: 0.72,
        ISSUE_PROMPT_DRIFT: 0.65,
        ISSUE_TIMEOUT: 0.88,
        ISSUE_NONE: 0.95,
    }.get(issue, 0.6)


def _suggestion(issue: str) -> str:
    return {
        ISSUE_AGENT_LOOP: (
            "检测到 Agent 循环：相同工具与入参被重复调用。"
            "建议降低 max_iterations、收紧工具 schema，或在 Prompt 中明确终止条件。"
        ),
        ISSUE_TOOL_FAILURE: (
            "工具调用链出现错误响应。建议检查下游 API 可用性、鉴权与超时；"
            "对失败工具增加重试/熔断，并在 Observation 中返回结构化错误码。"
        ),
        ISSUE_TOKEN_DRIFT: (
            "Token 消耗呈异常增长。建议压缩上下文、启用摘要、限制历史轮次，"
            "并对比 Prompt 版本避免无必要的长上下文注入。"
        ),
        ISSUE_PROMPT_DRIFT: (
            "不同 Prompt 版本评分波动较大。建议固定 prompt_version、做 A/B 对比，"
            "并回滚到表现更稳的模板。"
        ),
        ISSUE_TIMEOUT: (
            "任务/轨迹超时。建议提高超时阈值、优化慢工具，或对长链路拆分为子任务。"
        ),
        ISSUE_NONE: "未发现明显故障模式。可继续用 Evaluation Analytics 观察趋势。",
    }.get(issue, "请结合 Trace 步骤与评测分数进一步人工复核。")


def diagnose_from_traces(
    *,
    task: Task | None,
    traces: list[Trace],
    suites: list[TestSuite] | None = None,
) -> dict[str, Any]:
    """Produce a structured diagnosis payload for the Intelligence Center UI."""
    suites = suites or []
    analyses = [_analyze_trace_steps(list(t.steps or [])) for t in traces]
    failed = [t for t in traces if getattr(t.status, "value", t.status) == "failed"]
    success = [t for t in traces if getattr(t.status, "value", t.status) == "success"]

    issues: list[dict[str, Any]] = []

    # Agent loop
    loop_hits = [a for a in analyses if a["loop_detected"]]
    if loop_hits:
        max_loop = max(a["loop_count"] for a in loop_hits)
        issues.append(
            {
                "issue": ISSUE_AGENT_LOOP,
                "confidence": _confidence(ISSUE_AGENT_LOOP),
                "root_cause": f"检测到 {len(loop_hits)} 条轨迹存在重复工具调用（最大循环次数 {max_loop}）。",
                "suggestion": _suggestion(ISSUE_AGENT_LOOP),
                "evidence": {
                    "loop_count": max_loop,
                    "affected_traces": len(loop_hits),
                    "avg_actions": round(
                        sum(a["action_count"] for a in loop_hits) / len(loop_hits), 2
                    ),
                },
            }
        )

    # Tool failure
    tool_error_traces = sum(1 for a in analyses if a["errors"])
    if tool_error_traces or failed:
        err_samples: list[str] = []
        for a in analyses:
            err_samples.extend(a["errors"][:2])
        if tool_error_traces or err_samples:
            issues.append(
                {
                    "issue": ISSUE_TOOL_FAILURE,
                    "confidence": _confidence(ISSUE_TOOL_FAILURE),
                    "root_cause": (
                        f"{tool_error_traces} 条轨迹 Observation 含错误信号；"
                        f"失败轨迹 {len(failed)} 条。"
                    ),
                    "suggestion": _suggestion(ISSUE_TOOL_FAILURE),
                    "evidence": {
                        "error_samples": err_samples[:5],
                        "failed_traces": len(failed),
                        "tools": list(
                            {
                                n
                                for a in analyses
                                for n in a["tool_names"]
                            }
                        )[:12],
                    },
                }
            )

    # Token drift
    growths = [a["token_growth_ratio"] for a in analyses if a["token_series"]]
    high_tokens = [t for t in traces if (t.total_tokens or 0) > 8000]
    if (growths and max(growths) > 1.5) or len(high_tokens) >= max(1, len(traces) // 3):
        issues.append(
            {
                "issue": ISSUE_TOKEN_DRIFT,
                "confidence": _confidence(ISSUE_TOKEN_DRIFT),
                "root_cause": "Token 使用量偏高或步进增长过快，可能存在上下文膨胀。",
                "suggestion": _suggestion(ISSUE_TOKEN_DRIFT),
                "evidence": {
                    "max_growth_ratio": max(growths) if growths else 0,
                    "high_token_traces": len(high_tokens),
                    "avg_tokens": round(
                        sum(t.total_tokens or 0 for t in traces) / max(len(traces), 1), 1
                    ),
                    "token_curve": [
                        {"trace_id": t.id, "tokens": t.total_tokens or 0}
                        for t in traces[:30]
                    ],
                },
            }
        )

    # Prompt drift (by prompt_version scores variance)
    by_prompt: dict[str, list[float]] = {}
    for t in traces:
        pv = getattr(t, "prompt_version", None) or "default"
        scores = [ms.score for ms in (t.metric_scores or [])]
        if scores:
            by_prompt.setdefault(pv, []).append(sum(scores) / len(scores))
    if len(by_prompt) >= 2:
        means = {k: sum(v) / len(v) for k, v in by_prompt.items() if v}
        if means and (max(means.values()) - min(means.values())) >= 8:
            issues.append(
                {
                    "issue": ISSUE_PROMPT_DRIFT,
                    "confidence": _confidence(ISSUE_PROMPT_DRIFT),
                    "root_cause": "不同 Prompt 版本平均分差异显著，存在 Prompt Drift。",
                    "suggestion": _suggestion(ISSUE_PROMPT_DRIFT),
                    "evidence": {
                        "prompt_means": {k: round(v, 2) for k, v in means.items()},
                    },
                }
            )

    # Task-level timeout / failed
    task_status = getattr(task.status, "value", None) if task else None
    if task_status in {"timeout", "failed"} and not issues:
        issue = ISSUE_TIMEOUT if task_status == "timeout" else ISSUE_TOOL_FAILURE
        issues.append(
            {
                "issue": issue,
                "confidence": _confidence(issue),
                "root_cause": f"任务状态为 {task_status}。",
                "suggestion": _suggestion(issue),
                "evidence": {"task_status": task_status},
            }
        )

    if not issues:
        issues.append(
            {
                "issue": ISSUE_NONE,
                "confidence": _confidence(ISSUE_NONE),
                "root_cause": "当前样本未命中已知故障模式。",
                "suggestion": _suggestion(ISSUE_NONE),
                "evidence": {
                    "trace_count": len(traces),
                    "success_count": len(success),
                    "failed_count": len(failed),
                },
            }
        )

    primary = issues[0]
    # Prefer non-healthy if present
    for it in issues:
        if it["issue"] != ISSUE_NONE:
            primary = it
            break

    # Topology for UI (Agent → Tool → API style)
    topology_nodes = [
        {"id": "user", "label": "User Request", "status": "ok"},
        {
            "id": "planner",
            "label": "Planner / Agent",
            "status": "warn" if primary["issue"] == ISSUE_AGENT_LOOP else "ok",
        },
        {
            "id": "tool",
            "label": "Tool Calling",
            "status": "error" if primary["issue"] == ISSUE_TOOL_FAILURE else "ok",
        },
        {"id": "observe", "label": "Observation", "status": "ok"},
        {
            "id": "judge",
            "label": "Judge",
            "status": "ok" if success else "warn",
        },
    ]
    topology_edges = [
        {"source": "user", "target": "planner"},
        {"source": "planner", "target": "tool"},
        {"source": "tool", "target": "observe"},
        {"source": "observe", "target": "judge"},
    ]
    if primary["issue"] == ISSUE_AGENT_LOOP:
        topology_edges.append({"source": "observe", "target": "planner", "type": "loop"})

    return {
        "task_id": task.id if task else None,
        "task_name": task.name if task else None,
        "task_status": task_status,
        "issue": primary["issue"],
        "confidence": primary["confidence"],
        "root_cause": primary["root_cause"],
        "suggestion": primary["suggestion"],
        "issues": issues,
        "summary": {
            "traces_total": len(traces),
            "traces_success": len(success),
            "traces_failed": len(failed),
            "suites_total": len(suites),
            "avg_latency_ms": round(
                sum(t.response_time_ms or 0 for t in traces) / max(len(traces), 1), 1
            ),
            "total_tokens": sum(t.total_tokens or 0 for t in traces),
            "total_cost": round(sum(float(getattr(t, "cost", 0) or 0) for t in traces), 6),
        },
        "topology": {"nodes": topology_nodes, "edges": topology_edges},
        "token_curve": [
            {
                "trace_id": t.id,
                "tokens": t.total_tokens or 0,
                "latency_ms": t.response_time_ms or 0,
                "status": getattr(t.status, "value", str(t.status)),
            }
            for t in traces[:50]
        ],
        "prompt_versions": list(
            {
                getattr(t, "prompt_version", None) or "default"
                for t in traces
            }
        ),
    }


async def diagnose_task(
    session: AsyncSession,
    task_id: str,
    *,
    actor: str | None = None,
) -> dict[str, Any] | None:
    """Load task + traces and run diagnosis. Returns None if task missing."""
    from app.core.tenancy import apply_owner_filter

    q = select(Task).where(Task.id == task_id)
    if actor:
        q = apply_owner_filter(q, actor)
    task = (await session.execute(q)).scalar_one_or_none()
    if not task:
        return None

    suites_q = select(TestSuite).where(TestSuite.task_id == task_id)
    suites = list((await session.execute(suites_q)).scalars().all())
    suite_ids = [s.id for s in suites]

    traces: list[Trace] = []
    if suite_ids:
        tq = (
            select(Trace)
            .where(Trace.test_suite_id.in_(suite_ids))
            .options(selectinload(Trace.metric_scores))
            .order_by(Trace.created_at.desc())
            .limit(100)
        )
        traces = list((await session.execute(tq)).scalars().unique().all())

    return diagnose_from_traces(task=task, traces=traces, suites=suites)
