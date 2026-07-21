# (c) 2026 AgentFlow-Eval
"""Phase 3: scorecard parse, weights, and LLMJudge rule path."""

from __future__ import annotations

import pytest

from app.core.judge_engine.llm_judge import LLMJudge
from app.core.judge_engine.scorecard import (
    DIMENSION_WEIGHTS,
    default_scorecard,
    extract_judge_config_from_agent_config,
    extract_scorecard_from_agent_config,
    parse_scorecard,
)
from app.core.celery_app.tasks import build_llm_judge


class TestScorecardModel:
    def test_default_weights(self) -> None:
        sc = default_scorecard()
        assert abs(sum(d.weight for d in sc.dimensions) - 100) < 0.01
        assert DIMENSION_WEIGHTS["tool_accuracy"] == 40.0

    def test_normalize_weights(self) -> None:
        sc = parse_scorecard(
            {
                "name": "custom",
                "dimensions": [
                    {"key": "a", "weight": 1, "method": "lexical"},
                    {"key": "b", "weight": 1, "method": "llm_only"},
                ],
            }
        )
        assert abs(sum(d.weight for d in sc.dimensions) - 100) < 0.01

    def test_extract_from_agent_config(self) -> None:
        sc = extract_scorecard_from_agent_config(
            {
                "model": "gpt-4o",
                "scorecard": {
                    "dimensions": [
                        {
                            "key": "quality",
                            "weight": 100,
                            "method": "lexical",
                            "label": "质量",
                        }
                    ]
                },
            }
        )
        assert sc.dimensions[0].key == "quality"
        assert abs(sc.dimensions[0].weight - 100) < 0.01

    def test_judge_config_extract(self) -> None:
        cfg = extract_judge_config_from_agent_config(
            {"scorecard": {"dimensions": [{"key": "x", "weight": 100, "method": "rule_tool"}]}}
        )
        assert "scorecard" in cfg


class TestJudgeWithScorecard:
    @pytest.fixture
    def steps(self):
        return [
            {
                "iteration": 0,
                "thought": "Search",
                "action": "web_search",
                "action_input": "q",
                "observation": "ok",
                "tokens": 10,
            },
            {
                "iteration": 1,
                "thought": "Done",
                "action": "final_answer",
                "action_input": "sunny 25C",
                "observation": "",
                "tokens": 5,
            },
        ]

    @pytest.mark.asyncio
    async def test_default_ranges(self, steps) -> None:
        judge = LLMJudge(api_key="")
        result = await judge.evaluate(steps, "sunny 25C", ["web_search"])
        s = result["scores"]
        assert 0 <= s["tool_accuracy"] <= 40
        assert 0 <= s["answer_correctness"] <= 40
        assert 0 <= s["reasoning_coherence"] <= 20
        assert 0 <= result["total"] <= 100

    @pytest.mark.asyncio
    async def test_custom_weights_applied(self, steps) -> None:
        sc = parse_scorecard(
            {
                "name": "tools_only",
                "dimensions": [
                    {
                        "key": "tool_accuracy",
                        "weight": 100,
                        "method": "rule_tool",
                        "label": "Tools",
                    }
                ],
            }
        )
        judge = LLMJudge(api_key="", scorecard=sc)
        result = await judge.evaluate(steps, "sunny 25C", ["web_search"])
        assert set(result["scores"].keys()) == {"tool_accuracy"}
        assert 0 <= result["scores"]["tool_accuracy"] <= 100
        assert abs(result["total"] - result["scores"]["tool_accuracy"]) < 0.01

    def test_build_llm_judge_passes_scorecard(self) -> None:
        judge = build_llm_judge(
            {
                "scorecard": {
                    "dimensions": [
                        {
                            "key": "tool_accuracy",
                            "weight": 50,
                            "method": "rule_tool",
                        },
                        {
                            "key": "answer_correctness",
                            "weight": 50,
                            "method": "lexical",
                        },
                    ]
                }
            }
        )
        assert isinstance(judge, LLMJudge)
        assert abs(sum(d.weight for d in judge.scorecard.dimensions) - 100) < 0.01
