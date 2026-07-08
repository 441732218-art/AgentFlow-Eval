# (c) 2026 AgentFlow-Eval
"""Trace and MetricScore Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetricScoreResponse(BaseModel):
    """Metric score response schema."""

    id: str
    metric_name: str
    score: float
    reason: str
    extra_metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class TraceResponse(BaseModel):
    """Execution trace response schema."""

    id: str
    test_suite_id: str
    user_query: str
    steps: list[dict[str, Any]]
    total_tokens: int
    response_time_ms: int
    status: str
    created_at: datetime | None = None
    metric_scores: list[MetricScoreResponse] = []

    model_config = {"from_attributes": True}


class TraceListResponse(BaseModel):
    """Trace list response schema."""

    items: list[TraceResponse]
    total: int


class JudgeResultResponse(BaseModel):
    """LLM Judge scoring result schema."""

    scores: dict[str, float] = Field(..., description="scores per dimension")
    total: float = Field(..., ge=0, le=100, description="weighted total score")
    reason: str = Field("", description="deduction reason details")
    token_cost: int = Field(0, description="tokens consumed by judge")
