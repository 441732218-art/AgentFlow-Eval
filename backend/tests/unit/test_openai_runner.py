# (c) 2026 AgentFlow-Eval
"""Tests for OpenAIReActRunner."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.agent_runner.openai_runner import OpenAIReActRunner, ToolDefinition


class TestOpenAIReActRunner:
    """Test suite for OpenAIReActRunner."""

    @pytest.fixture
    def mock_async_openai(self):
        """Patch AsyncOpenAI constructor."""
        with patch("app.core.agent_runner.openai_runner.AsyncOpenAI") as mock:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_react_loop_success(self, mock_async_openai):
        """ReAct loop should complete with final_answer in function-calling mode."""
        from tests.unit.conftest import make_mock_response, make_mock_tool_call

        tc = make_mock_tool_call("web_search", '{"query": "test"}')
        resp1 = make_mock_response(content="Need to search", tool_calls=[tc])
        resp2 = make_mock_response(content="Thought: Done\nAction: final_answer\nAction Input: The answer is 42.")

        mock_async_openai.chat.completions.create.side_effect = [resp1, resp2]

        runner = OpenAIReActRunner(model="gpt-4o-mini", max_iterations=5)
        result = await runner.run("Test query", tools=[])

        assert result["status"] == "success"
        assert len(result["steps"]) >= 1
        assert result["final_answer"] is not None
        assert result["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_react_loop_text_mode(self, mock_async_openai):
        """ReAct loop should parse text output."""
        from tests.unit.conftest import make_mock_response

        text = "Thought: I have it.\nAction: final_answer\nAction Input: The result is 42."
        mock_async_openai.chat.completions.create.side_effect = [make_mock_response(content=text)]

        runner = OpenAIReActRunner(model="gpt-4o-mini", max_iterations=5)
        result = await runner.run("Quick query")

        assert result["status"] == "success"
        assert "42" in (result.get("final_answer") or "")

    @pytest.mark.asyncio
    async def test_max_iterations(self, mock_async_openai):
        """Should set status to max_iterations_reached when limit hit."""
        from tests.unit.conftest import make_mock_response, make_mock_tool_call

        tc = make_mock_tool_call("web_search", '{"query": "x"}')
        resp = make_mock_response(content="Still thinking...", tool_calls=[tc])
        mock_async_openai.chat.completions.create.side_effect = [resp] * 10

        runner = OpenAIReActRunner(model="gpt-4o-mini", max_iterations=2)
        result = await runner.run("Endless query")

        assert result["status"] == "max_iterations_reached"
        assert result["iterations"] <= 3

    @pytest.mark.asyncio
    async def test_custom_tool_execution(self):
        """Custom ToolDefinition with fn should be executed."""
        def my_tool(query: str) -> str:
            return f"Result for: {query}"

        runner = OpenAIReActRunner(api_key="sk-test")
        tool = ToolDefinition(name="my_search", description="Test tool", fn=my_tool)
        result = runner._execute_tool("my_search", {"query": "hello"}, {"my_search": tool})
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_empty_query(self, mock_async_openai):
        """Empty query should still produce a valid result."""
        from tests.unit.conftest import make_mock_response

        mock_async_openai.chat.completions.create.side_effect = [
            make_mock_response(content="Thought: Nothing.\nAction: final_answer\nAction Input: OK.")
        ]
        runner = OpenAIReActRunner(model="gpt-4o-mini", max_iterations=3)
        result = await runner.run("")
        assert result["status"] in ("success", "max_iterations_reached")

    @pytest.mark.asyncio
    async def test_tool_calls_tracked(self, mock_async_openai):
        """Steps should contain tool call information."""
        from tests.unit.conftest import make_mock_response, make_mock_tool_call

        tc = make_mock_tool_call("web_search", '{"query": "test"}')
        resp1 = make_mock_response(content="Searching...", tool_calls=[tc])
        resp2 = make_mock_response(content="Thought: Done\nAction: final_answer\nAction Input: Result.")
        mock_async_openai.chat.completions.create.side_effect = [resp1, resp2]

        runner = OpenAIReActRunner(model="gpt-4o-mini", max_iterations=5)
        result = await runner.run("Test query")
        actions = [s.get("action") for s in result.get("steps", [])]
        assert "web_search" in actions or "final_answer" in actions

