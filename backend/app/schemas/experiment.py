# (c) 2026 AgentFlow-Eval
"""Pydantic schemas for Experiment comparison APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SuiteCase(BaseModel):
    """Single test case in an experiment suite snapshot."""

    user_query: str = Field(..., min_length=1)
    expected_output: str = Field(default="")
    expected_tools: list[str] = Field(default_factory=list)


class ExperimentVariant(BaseModel):
    """One agent configuration variant to compare."""

    label: str = Field(..., min_length=1, max_length=100, description="变体标签")
    agent_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent 配置（runner/model/endpoint_url 等）",
    )


class ExperimentCreate(BaseModel):
    """Create experiment from base task and/or explicit suites + variants."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    base_task_id: str | None = Field(
        default=None,
        description="从已有任务复制测试套件（与 suites 二选一或合并）",
    )
    suites: list[SuiteCase] = Field(
        default_factory=list,
        description="显式用例列表；可与 base_task_id 并用",
    )
    variants: list[ExperimentVariant] = Field(
        ...,
        min_length=1,
        description="至少一个变体；创建后会为每个变体生成 Task 并排队执行",
    )
    auto_execute: bool = Field(
        default=True,
        description="是否立即排队执行各变体任务",
    )

    @field_validator("variants")
    @classmethod
    def unique_labels(cls, v: list[ExperimentVariant]) -> list[ExperimentVariant]:
        labels = [x.label for x in v]
        if len(labels) != len(set(labels)):
            raise ValueError("variant labels must be unique within an experiment")
        return v


class ExperimentRunResponse(BaseModel):
    """Single run in list/detail responses."""

    id: str
    experiment_id: str
    task_id: str
    label: str
    agent_config: dict[str, Any]
    task_status: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExperimentResponse(BaseModel):
    """Experiment detail."""

    id: str
    name: str
    description: str
    base_task_id: str | None = None
    suite_count: int = 0
    created_by: str = "anonymous"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    runs: list[ExperimentRunResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ExperimentListResponse(BaseModel):
    """Paginated experiment list."""

    items: list[ExperimentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class RunCompareItem(BaseModel):
    """Aggregated scores for one experiment run."""

    label: str
    task_id: str
    task_status: str
    average_score: float = 0.0
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    total_tokens: int = 0
    total_time_ms: int = 0
    suite_count: int = 0
    scored_traces: int = 0


class ExperimentCompareResponse(BaseModel):
    """Side-by-side comparison of experiment runs."""

    experiment_id: str
    name: str
    suite_count: int
    runs: list[RunCompareItem]
    best_label: str | None = None
    delta_vs_best: dict[str, float] = Field(
        default_factory=dict,
        description="各变体相对最高分的总分差值（best 为 0）",
    )
