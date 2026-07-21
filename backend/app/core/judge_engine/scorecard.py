# (c) 2026 AgentFlow-Eval
"""Configurable Judge scorecard (Phase 3).

Default card matches historical 40/40/20 dimensions so behavior is unchanged
when no custom scorecard is supplied.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DimensionMethod = Literal["rule_tool", "lexical", "llm_only", "llm_or_lexical"]

# Weights are points that sum to 100 (same scale as historical DIMENSION_WEIGHTS)
DEFAULT_WEIGHT_SUM = 100.0


class ScoreDimension(BaseModel):
    """One scoring dimension."""

    key: str = Field(..., min_length=1, max_length=64)
    label: str = Field(default="")
    weight: float = Field(..., gt=0, le=100)
    description: str = Field(default="")
    method: DimensionMethod = "llm_or_lexical"

    @field_validator("key")
    @classmethod
    def key_slug(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("dimension key required")
        return s


class Scorecard(BaseModel):
    """Rubric for hybrid rule + LLM judging."""

    version: int = 1
    name: str = "default_agent_eval"
    dimensions: list[ScoreDimension] = Field(min_length=1)
    llm_refine: bool = True
    # When True, re-scale weights so they sum to 100 if slightly off
    normalize_weights: bool = True

    @model_validator(mode="after")
    def check_weights(self) -> Scorecard:
        keys = [d.key for d in self.dimensions]
        if len(keys) != len(set(keys)):
            raise ValueError("dimension keys must be unique")
        total = sum(d.weight for d in self.dimensions)
        if total <= 0:
            raise ValueError("weights must sum to a positive value")
        if self.normalize_weights and abs(total - DEFAULT_WEIGHT_SUM) > 0.01:
            # Normalize to 100
            factor = DEFAULT_WEIGHT_SUM / total
            for d in self.dimensions:
                d.weight = round(d.weight * factor, 4)
        elif not self.normalize_weights and abs(total - DEFAULT_WEIGHT_SUM) > 0.5:
            raise ValueError(
                f"weights must sum to {DEFAULT_WEIGHT_SUM}, got {total}"
            )
        return self

    def weight_map(self) -> dict[str, float]:
        return {d.key: float(d.weight) for d in self.dimensions}

    def label_map(self) -> dict[str, str]:
        return {d.key: (d.label or d.key) for d in self.dimensions}

    def to_system_prompt(self) -> str:
        lines = [
            "You are a rigorous AI Agent evaluation expert.",
            "Score across the following dimensions (points as max for each):",
        ]
        for d in self.dimensions:
            desc = d.description or d.label or d.key
            lines.append(f"- {d.key} (0-{d.weight:g}): {desc}")
        lines.append(
            'Output ONLY valid JSON with fields: scores (object of dimension->number), '
            "total (sum of scores), reason (string)."
        )
        return "\n".join(lines)

    def to_public_dict(self) -> dict[str, Any]:
        return self.model_dump()


def default_scorecard() -> Scorecard:
    """Historical default: tool 40 + answer 40 + coherence 20."""
    return Scorecard(
        name="default_agent_eval",
        dimensions=[
            ScoreDimension(
                key="tool_accuracy",
                label="工具调用准确率",
                weight=40.0,
                description="是否按预期调用工具，有无多余/缺失",
                method="rule_tool",
            ),
            ScoreDimension(
                key="answer_correctness",
                label="答案准确性",
                weight=40.0,
                description="最终答案与 expected_output 一致性",
                method="llm_or_lexical",
            ),
            ScoreDimension(
                key="reasoning_coherence",
                label="推理连贯性",
                weight=20.0,
                description="步骤是否自洽、是否重复循环",
                method="llm_only",
            ),
        ],
        llm_refine=True,
    )


# Module-level singleton for imports that expect DIMENSION_WEIGHTS dict
DEFAULT_SCORECARD = default_scorecard()
DIMENSION_WEIGHTS: dict[str, float] = DEFAULT_SCORECARD.weight_map()


def parse_scorecard(data: Any) -> Scorecard:
    """Parse scorecard from dict / nested judge config; fall back to default."""
    if data is None:
        return default_scorecard()
    if isinstance(data, Scorecard):
        return data
    if not isinstance(data, dict):
        return default_scorecard()
    # Nested forms
    if "dimensions" in data:
        return Scorecard.model_validate(data)
    if "scorecard" in data and isinstance(data["scorecard"], dict):
        return Scorecard.model_validate(data["scorecard"])
    return default_scorecard()


def extract_scorecard_from_agent_config(
    agent_config: dict[str, Any] | None,
) -> Scorecard:
    """Resolve scorecard from Task.agent_config shapes."""
    cfg = dict(agent_config or {})
    if isinstance(cfg.get("scorecard"), dict):
        return parse_scorecard(cfg["scorecard"])
    judge = cfg.get("judge")
    if isinstance(judge, dict):
        if isinstance(judge.get("scorecard"), dict):
            return parse_scorecard(judge["scorecard"])
        if "dimensions" in judge:
            return parse_scorecard(judge)
    return default_scorecard()


def extract_judge_config_from_agent_config(
    agent_config: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build judge_config dict for build_llm_judge from task agent_config."""
    cfg = dict(agent_config or {})
    out: dict[str, Any] = {}
    judge = cfg.get("judge")
    if isinstance(judge, dict):
        out.update(judge)
    if isinstance(cfg.get("scorecard"), dict):
        out["scorecard"] = cfg["scorecard"]
    elif "scorecard" not in out:
        # always pass explicit default for cache key clarity optional
        pass
    return out
