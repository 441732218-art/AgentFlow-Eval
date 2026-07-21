# (c) 2026 AgentFlow-Eval
"""Shared fixtures and mock helpers for unit tests."""

from unittest.mock import MagicMock

SAMPLE_REACT_STEPS = [
    {
        "iteration": 0,
        "thought": "Need to search weather",
        "action": "web_search",
        "action_input": '{"query": "Beijing weather"}',
        "observation": "Sunny 25C",
        "tokens": 50,
    },
    {
        "iteration": 1,
        "thought": "Have answer",
        "action": "final_answer",
        "action_input": "The weather in Beijing is sunny and 25 degrees.",
        "observation": "",
        "tokens": 30,
    },
]


def make_mock_response(content=None, tool_calls=None, total_tokens=100):
    resp = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    resp.choices = [choice]
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = total_tokens // 2
    resp.usage.completion_tokens = total_tokens // 2
    resp.usage.total_tokens = total_tokens
    return resp


def make_mock_tool_call(name, args_json):
    tc = MagicMock()
    tc.id = "call_" + name
    tc.type = "function"
    tc.function.name = name
    tc.function.arguments = args_json
    return tc
