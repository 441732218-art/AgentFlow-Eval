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


class TokenUsage(BaseModel):
    """Token usage breakdown for observability UIs."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


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
    # Observability / version metadata (optional on older rows)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    agent_version: str | None = None
    prompt_version: str | None = None
    model_version: str | None = None
    tool_version: str | None = None
    token_usage: TokenUsage | None = None

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


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
