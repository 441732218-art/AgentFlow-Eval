# (c) 2026 AgentFlow-Eval
"""LLM Judge 与指标计算单元测试。"""

import pytest

from app.core.judge_engine.llm_judge import LLMJudge
from app.core.judge_engine.metrics import (
    _normalize,
    calc_tool_accuracy,
    extract_answer_text,
)


class TestLLMJudge:
    """LLM Judge 单元测试。"""

    @pytest.fixture
    def judge(self):
        # 无 API Key → 纯规则评分，单元测试可离线运行
        return LLMJudge(api_key="", model="gpt-4o-mini")

    @pytest.fixture
    def sample_steps(self):
        return [
            {
                "iteration": 0,
                "thought": "搜索相关信息",
                "action": "web_search",
                "action_input": '{"query": "人工智能"}',
                "observation": "人工智能是计算机科学的一个分支",
                "tokens": 50,
            },
            {
                "iteration": 1,
                "thought": "整理答案",
                "action": "final_answer",
                "action_input": "人工智能是计算机科学的一个分支。",
                "observation": "",
                "tokens": 30,
            },
        ]

    @pytest.mark.asyncio
    async def test_score_calculation(self, judge, sample_steps):
        """测试评分计算准确性（各维度分数在合法区间内）。"""
        result = await judge.evaluate(
            sample_steps,
            expected_output="人工智能是计算机科学的一个分支",
            expected_tools=["web_search"],
        )
        scores = result["scores"]
        assert 0 <= scores["tool_accuracy"] <= 40
        assert 0 <= scores["answer_correctness"] <= 40
        assert 0 <= scores["reasoning_coherence"] <= 20
        assert 0 <= result["total"] <= 100
        assert "reason" in result
        assert result["mode"] == "rule_only"

    @pytest.mark.asyncio
    async def test_cjk_text_handling(self, judge):
        """测试 CJK 文本在答案提取、分词与归一化中的处理。"""
        steps = [
            {
                "iteration": 0,
                "thought": "回答问题",
                "action": "final_answer",
                "action_input": "人工智能是计算机科学的一个分支",
                "observation": "",
                "tokens": 20,
            }
        ]
        answer = LLMJudge._extract_final_answer(steps)
        assert "人工智能" in answer

        tokens = judge.tokenize(answer)
        assert len(tokens) > 0
        assert any("人工" in t or "智能" in t or "人工智能" in t for t in tokens)

        normalized = _normalize(answer)
        assert "人工智能" in normalized
        assert len(normalized) > 0

        # 规则评分应能处理纯中文 expected/actual，不抛异常
        result = await judge.evaluate(steps, "人工智能是计算机科学的一个分支", [])
        assert isinstance(result, dict)
        assert "scores" in result
        assert result["scores"]["answer_correctness"] >= 30.0

    @pytest.mark.parametrize(
        "metric",
        ["tool_accuracy", "answer_correctness", "reasoning_coherence"],
    )
    @pytest.mark.asyncio
    async def test_all_metrics(self, judge, sample_steps, metric):
        """测试所有评估维度均出现在结果中。"""
        result = await judge.evaluate(
            sample_steps,
            expected_output="人工智能是计算机科学的一个分支",
            expected_tools=["web_search"],
        )
        assert metric in result["scores"]


class TestMetricsCalculator:
    """指标计算测试（metrics 模块轻量级辅助评分）。"""

    def test_tool_accuracy_score(self):
        """测试工具调用准确率计算。"""
        score, reason = calc_tool_accuracy(
            actual_tool_names=["web_search"],
            expected_tools=["web_search", "calculator"],
        )
        assert 0 <= score <= 100
        assert score < 100
        assert "缺少" in reason or "missing" in reason.lower()

    def test_tool_accuracy_perfect_match(self):
        """测试工具完全匹配时满分。"""
        score, reason = calc_tool_accuracy(
            actual_tool_names=["web_search"],
            expected_tools=["web_search"],
        )
        assert score == 100.0
        assert len(reason) > 0

    def test_extract_answer_cjk(self):
        """测试从步骤中提取中文答案。"""
        steps = [
            {"role": "user", "content": "什么是人工智能？"},
            {"role": "assistant", "content": "人工智能是计算机科学的一个分支"},
        ]
        answer = extract_answer_text(steps)
        assert "人工智能" in answer

    def test_normalize_cjk(self):
        """测试 CJK 文本归一化（空白与标点清理）。"""
        text = "人工智能，正在改变  世界！"
        normalized = _normalize(text)
        assert "人工智能" in normalized
        assert "世界" in normalized
        assert " " not in normalized
        assert "！" not in normalized
        assert "，" not in normalized
