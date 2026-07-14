# (c) 2026 AgentFlow-Eval
"""执行轨迹查询接口 —— 列表、详情、评分与人工审核（含 actor 隔离）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.core.tenancy import (
    apply_trace_owner_filter,
    load_task_for_suite,
    load_trace_with_access,
)
from app.models.metric_score import MetricScore
from app.models.test_suite import TestSuite
from app.models.trace import Trace
from app.schemas.trace import (
    JudgeResultResponse,
    MetricScoreResponse,
    TraceListResponse,
    TraceResponse,
)
from app.utils.exceptions import NotFoundError

router = APIRouter()


class HumanReviewRequest(BaseModel):
    """人工审核评分请求体。"""

    metric_name: str = Field(..., description="要审核的指标名称")
    human_score: float = Field(..., ge=0, le=100, description="人工评分 (0-100)")
    reviewer: str = Field(..., min_length=1, max_length=100, description="审核人标识")
    reason: str = Field("", description="审核备注")


class HumanReviewResponse(BaseModel):
    """人工审核评分响应。"""

    trace_id: str
    metric_name: str
    original_score: float
    human_score: float
    reviewer: str
    is_human_reviewed: bool


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


@router.get("", response_model=TraceListResponse)
async def list_traces(
    request: Request,
    test_suite_id: str | None = Query(None, description="按测试用例筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """获取执行轨迹列表（按任务归属隔离）。"""
    actor = _actor(request)

    if test_suite_id:
        # Ensure caller can access the suite's parent task
        await load_task_for_suite(session, test_suite_id, actor)

    query = select(Trace).options(selectinload(Trace.metric_scores))
    count_query = select(func.count(Trace.id))

    query = apply_trace_owner_filter(query, actor)
    count_query = apply_trace_owner_filter(count_query, actor)

    if test_suite_id:
        query = query.where(Trace.test_suite_id == test_suite_id)
        count_query = count_query.where(Trace.test_suite_id == test_suite_id)

    query = query.order_by(Trace.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(query)
    traces = result.scalars().unique().all()

    items = [_trace_to_response(t) for t in traces]
    return TraceListResponse(items=items, total=total)


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """获取单条执行轨迹（含评分），校验任务归属。"""
    trace = await load_trace_with_access(session, trace_id, _actor(request))
    return _trace_to_response(trace)


@router.post("/{trace_id}/judge", response_model=JudgeResultResponse)
async def judge_trace(
    trace_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """对指定轨迹执行 LLM-as-Judge 评分（需拥有所属任务）。"""
    trace = await load_trace_with_access(session, trace_id, _actor(request))

    if trace.metric_scores:
        scores = {ms.metric_name: ms.score for ms in trace.metric_scores}
        total = sum(scores.values())
        reason = trace.metric_scores[0].reason if trace.metric_scores else ""
        return JudgeResultResponse(
            scores=scores,
            total=total,
            reason=reason,
            token_cost=trace.metric_scores[0].extra_metadata.get("token_cost", 0)
            if trace.metric_scores[0].extra_metadata
            else 0,
        )

    suite_result = await session.execute(
        select(TestSuite).where(TestSuite.id == trace.test_suite_id)
    )
    suite = suite_result.scalar_one_or_none()
    if not suite:
        raise NotFoundError("测试用例", trace.test_suite_id)

    from app.core.judge_engine.llm_judge import LLMJudge

    judge = LLMJudge()
    judge_result = await judge.evaluate(
        trace_steps=trace.steps,
        expected_output=suite.expected_output,
        expected_tools=suite.expected_tools,
    )
    scores = judge_result.get("scores", {}) if isinstance(judge_result, dict) else judge_result.scores
    total = judge_result.get("total", 0.0) if isinstance(judge_result, dict) else judge_result.total
    reason = judge_result.get("reason", "") if isinstance(judge_result, dict) else judge_result.reason
    token_cost = judge_result.get("token_cost", 0) if isinstance(judge_result, dict) else judge_result.token_cost

    for metric_name, score in scores.items():
        ms = MetricScore(
            trace_id=trace_id,
            metric_name=metric_name,
            score=score,
            reason=reason,
            extra_metadata={"token_cost": token_cost},
        )
        session.add(ms)

    await session.commit()

    return JudgeResultResponse(
        scores=scores,
        total=total,
        reason=reason,
        token_cost=token_cost,
    )


@router.post("/{trace_id}/review", response_model=HumanReviewResponse)
async def review_trace(
    trace_id: str,
    body: HumanReviewRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """提交人工审核评分（需拥有所属任务）。"""
    trace = await load_trace_with_access(session, trace_id, _actor(request))

    existing_ms = None
    for ms in trace.metric_scores:
        if ms.metric_name == body.metric_name:
            existing_ms = ms
            break

    if existing_ms:
        original_score = existing_ms.score
        existing_ms.human_score = body.human_score
        existing_ms.is_human_reviewed = True
        existing_ms.reviewer = body.reviewer
        if body.reason:
            existing_ms.reason = body.reason
    else:
        original_score = 0.0
        new_ms = MetricScore(
            trace_id=trace_id,
            metric_name=body.metric_name,
            score=0.0,
            human_score=body.human_score,
            is_human_reviewed=True,
            reviewer=body.reviewer,
            reason=body.reason or "Human review",
        )
        session.add(new_ms)

    await session.commit()

    return HumanReviewResponse(
        trace_id=trace_id,
        metric_name=body.metric_name,
        original_score=original_score,
        human_score=body.human_score,
        reviewer=body.reviewer,
        is_human_reviewed=True,
    )


def _trace_to_response(trace: Trace) -> TraceResponse:
    """将 Trace ORM 对象转换为响应模型。"""
    return TraceResponse(
        id=trace.id,
        test_suite_id=trace.test_suite_id,
        user_query=trace.user_query,
        steps=trace.steps,
        total_tokens=trace.total_tokens,
        response_time_ms=trace.response_time_ms,
        status=trace.status.value,
        created_at=trace.created_at,
        metric_scores=[
            MetricScoreResponse(
                id=ms.id,
                metric_name=ms.metric_name,
                score=ms.score,
                reason=ms.reason,
                extra_metadata=ms.extra_metadata,
            )
            for ms in (trace.metric_scores or [])
        ],
    )
