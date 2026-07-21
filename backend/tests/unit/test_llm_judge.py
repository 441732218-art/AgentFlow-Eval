# (c) 2026 AgentFlow-Eval
"""Tests for LLMJudge scoring engine."""

import pytest
from app.core.judge_engine.llm_judge import LLMJudge
from app.core.judge_engine.metrics import calc_tool_accuracy, extract_answer_text


class TestLLMJudge:
    """Test suite for LLMJudge rule-based scoring mode."""

    @pytest.fixture
    def judge(self):
        return LLMJudge(api_key="")

    @pytest.fixture
    def sample_steps(self):
        return [
            {
                "iteration": 0,
                "thought": "Search weather",
                "action": "web_search",
                "action_input": '{"query": "Beijing"}',
                "observation": "Sunny 25C",
                "tokens": 50,
            },
            {
                "iteration": 1,
                "thought": "Done",
                "action": "final_answer",
                "action_input": "The weather is sunny 25C.",
                "observation": "",
                "tokens": 30,
            },
        ]

    @pytest.mark.asyncio
    async def test_rule_only_mode(self, judge, sample_steps):
        """Should return dict result in rule_only mode."""
        result = await judge.evaluate(sample_steps, "sunny 25C", ["web_search"])
        assert isinstance(result, dict)
        assert result["mode"] == "rule_only"

    @pytest.mark.asyncio
    async def test_dict_structure(self, judge, sample_steps):
        """Result should contain all expected fields."""
        result = await judge.evaluate(sample_steps, "sunny 25C", ["web_search"])
        assert "scores" in result
        assert "total" in result
        assert "reason" in result
        assert "details" in result
        assert "step_analysis" in result

    @pytest.mark.asyncio
    async def test_scores_valid_ranges(self, judge, sample_steps):
        """Scores should be within valid ranges."""
        result = await judge.evaluate(sample_steps, "sunny 25C", ["web_search"])
        s = result["scores"]
        assert 0 <= s["tool_accuracy"] <= 40
        assert 0 <= s["answer_correctness"] <= 40
        assert 0 <= s["reasoning_coherence"] <= 20
        assert 0 <= result["total"] <= 100

    @pytest.mark.asyncio
    async def test_tool_extraction(self, sample_steps):
        """Extract tool names from steps."""
        names = LLMJudge._extract_tool_names(sample_steps)
        assert "web_search" in names
        assert "final_answer" not in names

    @pytest.mark.asyncio
    async def test_answer_extraction(self, sample_steps):
        """Extract final answer from steps."""
        answer = LLMJudge._extract_final_answer(sample_steps)
        assert "25C" in answer

    @pytest.mark.asyncio
    async def test_step_analysis(self, sample_steps):
        """Step analysis should flag each steps type."""
        analysis = LLMJudge._analyze_steps(sample_steps, ["web_search"])
        assert len(analysis) == 2
        assert analysis[0]["has_thought"]
        assert analysis[0]["has_action"]
        assert analysis[0]["action_name"] == "web_search"

    @pytest.mark.asyncio
    async def test_empty_trace(self, judge):
        """Empty trace should return valid result."""
        result = await judge.evaluate([], "answer", [])
        assert isinstance(result, dict)
        assert result["total"] >= 0

    @pytest.mark.asyncio
    async def test_no_expected_tools(self, judge, sample_steps):
        """With no expected tools, tool_accuracy should be full score."""
        result = await judge.evaluate(sample_steps, "sunny 25C")
        assert result["scores"]["tool_accuracy"] == 40.0

    @pytest.mark.asyncio
    async def test_lexical_score(self):
        """Lexical overlap should work for answer scoring."""
        score, reason = LLMJudge._lexical_answer_score("sunny 25 degrees", "sunny 25")
        assert 0 <= score <= 40
        assert len(reason) > 0

    @pytest.mark.asyncio
    async def test_calc_tool_accuracy(self):
        """calc_tool_accuracy should penalize missing tools."""
        score, reason = calc_tool_accuracy(["search"], ["search", "db", "calc"])
        assert score < 100
        assert "missing" in reason.lower() or "缺少" in reason

    @pytest.mark.asyncio
    async def test_extract_answer_text(self):
        """extract_answer_text should get last assistant content."""
        steps = [
            {"role": "assistant", "content": "first"},
            {"role": "user", "content": "query"},
            {"role": "assistant", "content": "final answer"},
        ]
        result = extract_answer_text(steps)
        assert result == "final answer"
