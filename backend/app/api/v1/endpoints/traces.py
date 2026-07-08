# ? 2026 AgentFlow-Eval
"""ִ?й켣??ѯ?ӿ? ???? ?ṩ Trace ???б???ѯ??????鿴???ܡ?"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.models.metric_score import MetricScore
from app.models.trace import Trace
from app.models.test_suite import TestSuite
from app.schemas.trace import JudgeResultResponse, MetricScoreResponse, TraceListResponse, TraceResponse
from app.utils.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=TraceListResponse)
async def list_traces(
    test_suite_id: str | None = Query(None, description="??????????ɸѡ"),
    page: int = Query(1, ge=1, description="ҳ??"),
    page_size: int = Query(20, ge=1, le=100, description="ÿҳ????"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """??ȡִ?й켣?б???֧?ְ?????????ɸѡ?ͷ?ҳ??"""
    query = select(Trace).options(selectinload(Trace.metric_scores))
    count_query = select(func.count(Trace.id))

    if test_suite_id:
        query = query.where(Trace.test_suite_id == test_suite_id)
        count_query = count_query.where(Trace.test_suite_id == test_suite_id)

    query = query.order_by(Trace.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(query)
    traces = result.scalars().all()

    items = [_trace_to_response(t) for t in traces]

    return TraceListResponse(items=items, total=total)


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """??ȡ????ִ?й켣????ϸ??Ϣ?????????????ݡ?"""
    result = await session.execute(
        select(Trace)
        .options(selectinload(Trace.metric_scores))
        .where(Trace.id == trace_id)
    )
    trace = result.scalar_one_or_none()
    if not trace:
        raise NotFoundError("ִ?й켣", trace_id)

    return _trace_to_response(trace)


@router.post("/{trace_id}/judge", response_model=JudgeResultResponse)
async def judge_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """??ָ???켣ִ?? LLM-as-Judge ???֡?

    ????ù켣???????ּ?¼??ֱ?ӷ??????????֣?
    ??????? LLM Judge ??????????ֲ??־û???
    """
    result = await session.execute(
        select(Trace)
        .options(selectinload(Trace.metric_scores))
        .where(Trace.id == trace_id)
    )
    trace = result.scalar_one_or_none()
    if not trace:
        raise NotFoundError("ִ?й켣", trace_id)

    # ????Ƿ?????????
    if trace.metric_scores:
        # ???????֣?ֱ?ӷ???
        scores = {ms.metric_name: ms.score for ms in trace.metric_scores}
        total = sum(scores.values())
        reason = trace.metric_scores[0].reason if trace.metric_scores else ""
        return JudgeResultResponse(
            scores=scores,
            total=total,
            reason=reason,
            token_cost=trace.metric_scores[0].extra_metadata.get("token_cost", 0)
            if trace.metric_scores[0].extra_metadata else 0,
        )

    # ??ȡ??Ӧ?? TestSuite ?Ի?ȡԤ????Ϣ
    suite_result = await session.execute(
        select(TestSuite).where(TestSuite.id == trace.test_suite_id)
    )
    suite = suite_result.scalar_one_or_none()
    if not suite:
        raise NotFoundError("????????", trace.test_suite_id)

    # ???? LLM Judge
    from app.core.judge_engine.llm_judge import LLMJudge

    judge = LLMJudge()
    judge_result = await judge.evaluate(
        trace_steps=trace.steps,
        expected_output=suite.expected_output,
        expected_tools=suite.expected_tools,
    )

    # ?־û?????
    token_cost = 0
    for metric_name, score in judge_result.scores.items():
        ms = MetricScore(
            trace_id=trace_id,
            metric_name=metric_name,
            score=score,
            reason=judge_result.reason,
            extra_metadata={"token_cost": judge_result.token_cost},
        )
        session.add(ms)
        token_cost += judge_result.token_cost

    await session.commit()

    return JudgeResultResponse(
        scores=judge_result.scores,
        total=judge_result.total,
        reason=judge_result.reason,
        token_cost=judge_result.token_cost,
    )


def _trace_to_response(trace: Trace) -> TraceResponse:
    """?? Trace ORM ????ת??Ϊ??Ӧģ?͡?"""
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


