# (c) 2026 AgentFlow-Eval
"""Schemas for online A/B testing APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ABVariantCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(default="")
    weight: float = Field(default=1.0, gt=0)
    is_control: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class ABExperimentCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    primary_metric: str = Field(default="conversion")
    alpha: float = Field(default=0.05, gt=0, lt=1)
    min_sample_size: int = Field(default=100, ge=1)
    variants: list[ABVariantCreate] = Field(..., min_length=2)
    source_experiment_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    start_immediately: bool = False

    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v: list[ABVariantCreate]) -> list[ABVariantCreate]:
        keys = [x.key for x in v]
        if len(keys) != len(set(keys)):
            raise ValueError("variant keys must be unique")
        controls = [x for x in v if x.is_control]
        if len(controls) > 1:
            raise ValueError("at most one control variant")
        return v


class ABVariantResponse(BaseModel):
    id: str
    key: str
    name: str
    weight: float
    is_control: bool
    payload: dict[str, Any] = Field(default_factory=dict)
    description: str = ""

    model_config = {"from_attributes": True}


class ABExperimentResponse(BaseModel):
    id: str
    key: str
    name: str
    description: str
    status: str
    alpha: float
    min_sample_size: int
    primary_metric: str
    control_variant_key: str | None = None
    source_experiment_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "anonymous"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    winner_variant_key: str | None = None
    created_at: datetime | None = None
    variants: list[ABVariantResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ABExperimentListResponse(BaseModel):
    items: list[ABExperimentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ABAssignRequest(BaseModel):
    unit_id: str = Field(..., min_length=1, max_length=128)
    context: dict[str, Any] | None = None
    record_exposure: bool = True


class ABAssignResponse(BaseModel):
    experiment_id: str
    experiment_key: str
    unit_id: str
    variant_key: str
    bucket: int
    is_new: bool
    is_control: bool
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str


class ABTrackRequest(BaseModel):
    unit_id: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., description="exposure | conversion | metric")
    metric_name: str | None = None
    metric_value: float | None = None
    properties: dict[str, Any] | None = None
    auto_assign: bool = True


class ABSampleSizeRequest(BaseModel):
    baseline_rate: float = Field(..., ge=0, le=1)
    mde: float = Field(..., gt=0, le=1, description="Absolute minimum detectable effect")
    alpha: float = Field(default=0.05, gt=0, lt=1)
    power: float = Field(default=0.8, gt=0, lt=1)


class ABStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(draft|running|paused|completed|archived)$")
