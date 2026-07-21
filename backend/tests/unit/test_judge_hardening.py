# (c) 2026 AgentFlow-Eval
"""Hardening tests for LLMJudge: cache, timeout, CJK, edges."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.judge_engine.llm_judge import LLMJudge


@pytest.fixture(autouse=True)
def _clear_cache():
    LLMJudge.clear_cache()
    yield
    LLMJudge.clear_cache()


@pytest.fixture
def judge() -> LLMJudge:
    return LLMJudge(api_key="", timeout_sec=0, cache_size=8)


class TestTokenizeAndCJK:
    def test_tokenize_english(self) -> None:
        tokens = LLMJudge.tokenize("The Cat sat on the mat")
        assert "cat" in tokens
        assert "mat" in tokens

    def test_tokenize_cjk(self) -> None:
        tokens = LLMJudge.tokenize("人工智能是计算机科学的一个分支")
        assert len(tokens) > 0
        assert any("人工" in t or "智能" in t or "人工智能" in t for t in tokens)

    def test_cjk_lexical_score_high(self) -> None:
        score, reason = LLMJudge._lexical_answer_score(
            "人工智能是计算机科学的一个分支",
            "人工智能是计算机科学的一个分支",
        )
        assert score >= 30.0
        assert len(reason) > 0

    def test_cjk_partial_overlap(self) -> None:
        score, _ = LLMJudge._lexical_answer_score(
            "AI正在改变世界",
            "人工智能正在改变世界",
        )
        # Bigram fallback should yield non-zero for shared "正在改变世界"
        assert score > 0


class TestCache:
    @pytest.mark.asyncio
    async def test_cache_hit(self, judge: LLMJudge) -> None:
        steps = [
            {
                "thought": "done",
                "action": "final_answer",
                "action_input": "hello world",
            }
        ]
        r1 = await judge.evaluate(steps, "hello world", [])
        r2 = await judge.evaluate(steps, "hello world", [])
        assert r1["cache_hit"] is False
        assert r2["cache_hit"] is True
        assert r1["total"] == r2["total"]

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self) -> None:
        j = LLMJudge(api_key="", timeout_sec=0, cache_size=2)
        LLMJudge.clear_cache()
        for i in range(3):
            await j.evaluate(
                [{"action": "final_answer", "action_input": f"ans-{i}"}],
                f"ans-{i}",
                [],
            )
        # Cache capacity is 2; first entry should be gone
        assert len(LLMJudge._cache) <= 2


class TestTimeoutAndEdges:
    @pytest.mark.asyncio
    async def test_timeout_falls_back_to_rule(self) -> None:
        j = LLMJudge(api_key="fake-key", timeout_sec=0.05, cache_size=0)
        j.has_api_key = True
        j.client = object()  # truthy

        async def slow_do_evaluate(*_a, **_k):
            await asyncio.sleep(1.0)
            return {
                "mode": "hybrid",
                "scores": {
                    "tool_accuracy": 0.0,
                    "answer_correctness": 0.0,
                    "reasoning_coherence": 0.0,
                },
                "total": 0.0,
                "reason": "late",
                "token_cost": 0,
            }

        with patch.object(
            j, "_do_evaluate", new=AsyncMock(side_effect=slow_do_evaluate)
        ):
            result = await j.evaluate(
                [{"action": "final_answer", "action_input": "x"}],
                "x",
                [],
            )
        assert isinstance(result, dict)
        assert result["mode"] == "rule_only"
        assert "timeout" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_none_steps(self, judge: LLMJudge) -> None:
        result = await judge.evaluate(None, "expected", None)  # type: ignore[arg-type]
        assert isinstance(result, dict)
        assert "scores" in result
        assert result["mode"] == "rule_only"

    @pytest.mark.asyncio
    async def test_empty_expected_tools_full_tool_score(self, judge: LLMJudge) -> None:
        steps = [
            {"action": "web_search", "thought": "s"},
            {"action": "final_answer", "action_input": "ok"},
        ]
        result = await judge.evaluate(steps, "ok", [])
        assert result["scores"]["tool_accuracy"] == 40.0

    @pytest.mark.asyncio
    async def test_malformed_step_dicts(self, judge: LLMJudge) -> None:
        steps = [{"foo": "bar"}, {}, {"action": "final_answer", "action_input": "42"}]
        result = await judge.evaluate(steps, "42", ["web_search"])
        assert 0 <= result["total"] <= 100

    def test_coherence_repetition_and_long_trace(self) -> None:
        long_steps = [
            {"thought": "same thought repeated often", "action": "web_search"}
            for _ in range(12)
        ]
        score, reason = LLMJudge._heuristic_coherence_score(long_steps)
        assert score < 20.0
        assert "Repetition" in reason or "iteration" in reason.lower()

    def test_deep_tuple_to_list(self) -> None:
        nested = (1, {"a": (2, 3)}, [4, (5,)])
        out = LLMJudge._deep_tuple_to_list(nested)
        assert out == [1, {"a": [2, 3]}, [4, [5]]]

    @pytest.mark.asyncio
    async def test_llm_refine_success_hybrid(self) -> None:
        j = LLMJudge(api_key="fake", timeout_sec=0, cache_size=0)
        j.has_api_key = True

        mock_usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        mock_msg = type("M", (), {"content": json_payload()})()
        mock_choice = type("C", (), {"message": mock_msg})()
        mock_resp = type("R", (), {"choices": [mock_choice], "usage": mock_usage})()

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_resp)
        j.client = client

        result = await j.evaluate(
            [{"action": "final_answer", "action_input": "42"}],
            "42",
            [],
        )
        assert result["mode"] == "hybrid"
        assert result["total"] == 95.0
        assert result["token_cost"] == 15

    @pytest.mark.asyncio
    async def test_llm_refine_invalid_json_falls_back(self) -> None:
        j = LLMJudge(api_key="fake", timeout_sec=0, cache_size=0)
        j.has_api_key = True

        mock_usage = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1})()
        mock_msg = type("M", (), {"content": "not-json{"})()
        mock_choice = type("C", (), {"message": mock_msg})()
        mock_resp = type("R", (), {"choices": [mock_choice], "usage": mock_usage})()

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_resp)
        j.client = client

        result = await j.evaluate(
            [{"action": "final_answer", "action_input": "x"}],
            "x",
            [],
        )
        assert result["mode"] == "rule_only"
        assert "LLM refine failed" in result["reason"]

    @pytest.mark.asyncio
    async def test_llm_refine_exception_falls_back(self) -> None:
        j = LLMJudge(api_key="fake", timeout_sec=0, cache_size=0)
        j.has_api_key = True
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(side_effect=ConnectionError("down"))
        j.client = client

        # Retry will re-raise after attempts; outer _do_evaluate catches generic Exception
        # tenacity retries ConnectionError — use RuntimeError to hit the outer catch
        client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

        result = await j.evaluate(
            [{"action": "final_answer", "action_input": "x"}],
            "x",
            [],
        )
        assert result["mode"] == "rule_only"


def json_payload() -> str:
    import json

    return json.dumps(
        {
            "scores": {
                "tool_accuracy": 40.0,
                "answer_correctness": 35.0,
                "reasoning_coherence": 20.0,
            },
            "total": 95.0,
            "reason": "refined",
        }
    )
