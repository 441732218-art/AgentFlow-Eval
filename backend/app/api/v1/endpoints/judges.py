# (c) 2026 AgentFlow-Eval
"""Judge scorecard defaults and validation (Phase 3)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.judge_engine.scorecard import (
    default_scorecard,
    parse_scorecard,
)
from app.core.rbac import Permission, require_permission
from app.utils.exceptions import ValidationError

router = APIRouter()


class ScorecardValidateRequest(BaseModel):
    scorecard: dict[str, Any] = Field(..., description="Scorecard JSON body")


@router.get("/scorecards/default")
@require_permission(Permission.TASK_READ)
async def get_default_scorecard(request: Request) -> dict[str, Any]:
    """Return the built-in 40/40/20 scorecard (compatible with legacy judges)."""
    sc = default_scorecard()
    return {
        "scorecard": sc.to_public_dict(),
        "weight_sum": sum(d.weight for d in sc.dimensions),
        "notes": "Weights are points summing to 100. Stored under Task.agent_config.scorecard.",
    }


@router.post("/scorecards/validate")
@require_permission(Permission.TASK_CREATE)
async def validate_scorecard(
    body: ScorecardValidateRequest,
    request: Request,
) -> dict[str, Any]:
    """Validate a custom scorecard (unique keys, positive weights, normalize to 100)."""
    try:
        sc = parse_scorecard(body.scorecard)
    except Exception as exc:
        raise ValidationError(str(exc)) from exc
    return {
        "ok": True,
        "scorecard": sc.to_public_dict(),
        "weight_sum": sum(d.weight for d in sc.dimensions),
    }
