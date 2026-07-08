# (c) 2026 AgentFlow-Eval
"""评测报告导出接口 —— 提供任务级别的汇总报告生成功能。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace
from app.utils.exceptions import NotFoundError

router = APIRouter()


@router.get("/{task_id}")
async def get_task_report(
    task_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """生成指定任务的完整评测报告。

    报告包含：
    - 任务基本信息
    - 测试用例总数与执行概况
    - 各维度平均分
    - 每个测试用例的详细评分
    - 耗时、Token 消耗统计
    """
    # 获取任务
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("任务", task_id)

    # 获取所有测试用例及其轨迹和评分
    suite_result = await session.execute(
        select(TestSuite)
        .options(
            selectinload(TestSuite.traces).selectinload(Trace.metric_scores),
        )
        .where(TestSuite.task_id == task_id)
    )
    suites = suite_result.scalars().all()

    # 统计汇总
    total_suites = len(suites)
    total_traces = 0
    total_tokens = 0
    total_time_ms = 0
    success_count = 0
    failed_count = 0

    # 维度汇总
    dimension_scores: dict[str, list[float]] = {}
    suite_details = []

    for suite in suites:
        traces = suite.traces or []
        trace_details = []

        for trace in traces:
            total_traces += 1
            total_tokens += trace.total_tokens
            total_time_ms += trace.response_time_ms

            if trace.status.value == "success":
                success_count += 1
            else:
                failed_count += 1

            scores_dict: dict[str, float] = {}
            for ms in trace.metric_scores or []:
                scores_dict[ms.metric_name] = ms.score
                if ms.metric_name not in dimension_scores:
                    dimension_scores[ms.metric_name] = []
                dimension_scores[ms.metric_name].append(ms.score)

            trace_details.append({
                "trace_id": trace.id,
                "status": trace.status.value,
                "total_tokens": trace.total_tokens,
                "response_time_ms": trace.response_time_ms,
                "scores": scores_dict,
                "created_at": trace.created_at.isoformat() if trace.created_at else None,
            })

        suite_details.append({
            "suite_id": suite.id,
            "user_query": suite.user_query,
            "expected_output": suite.expected_output,
            "expected_tools": suite.expected_tools,
            "traces": trace_details,
        })

    # 计算各维度平均分
    avg_dimension_scores: dict[str, float] = {}
    for dim, scores in dimension_scores.items():
        avg_dimension_scores[dim] = round(sum(scores) / len(scores), 1) if scores else 0.0

    # 总平均分
    all_scores = [s for scores in dimension_scores.values() for s in scores]
    overall_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        },
        "summary": {
            "total_suites": total_suites,
            "total_traces": total_traces,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_tokens": total_tokens,
            "total_time_ms": total_time_ms,
            "avg_time_per_trace_ms": round(total_time_ms / total_traces, 1) if total_traces else 0,
            "overall_score": overall_avg,
            "dimension_scores": avg_dimension_scores,
        },
        "details": suite_details,
    }
