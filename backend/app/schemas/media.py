# (c) 2026 AgentFlow-Eval
"""Pydantic schemas for multimodal media APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MediaAssetResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    media_kind: str
    storage_backend: str
    storage_key: str
    extracted_text: str = ""
    features: dict[str, Any] | None = None
    extract_meta: dict[str, Any] | None = None
    task_id: str | None = None
    test_suite_id: str | None = None
    created_by: str = "anonymous"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MediaExtractResponse(BaseModel):
    asset_id: str
    kind: str
    text: str
    features: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    pages: int | None = None
    tables: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MultimodalEvalRequest(BaseModel):
    """Evaluate a stored media asset (or re-score extraction)."""

    query: str = Field(default="", description="Evaluation question / prompt")
    expected_text: str = Field(default="", description="Expected content or caption")
    use_vision_llm: bool = Field(
        default=True,
        description="Use GPT-4V/gpt-4o style vision LLM when image + API key available",
    )
    model: str | None = Field(default=None, description="Override vision model")


class MultimodalEvalResponse(BaseModel):
    asset_id: str
    mode: str
    scores: dict[str, float]
    total: float
    reason: str
    kind: str
    token_cost: int = 0
    degraded: bool = False
    model: str | None = None
    extraction: MediaExtractResponse | None = None


class SupportedFormatsResponse(BaseModel):
    extensions: list[str]
    kinds: list[str]
    max_upload_bytes: int
    storage_backend: str
