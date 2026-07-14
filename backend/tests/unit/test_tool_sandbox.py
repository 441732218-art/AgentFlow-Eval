# (c) 2026 AgentFlow-Eval
"""Tests for tool sandbox registry and safe execution."""

from app.core.agent_runner.tool_sandbox import (
    BUILTIN_TOOLS,
    get_openai_tool_defs,
    resolve_tools_for_suite,
    run_tool_sandboxed,
    tool_calculator,
    tool_json_get,
)


class TestToolSandbox:
    def test_calculator_safe_math(self):
        assert "6" in tool_calculator("(1+2)*2") or "6.0" in tool_calculator("(1+2)*2")

    def test_calculator_rejects_names(self):
        out = tool_calculator("__import__('os').system('echo x')")
        assert "Error" in out

    def test_json_get(self):
        out = tool_json_get(data='{"user":{"name":"Ada"}}', path="user.name")
        assert out == "Ada"

    def test_unknown_tool_denied(self):
        out = run_tool_sandboxed("rm_rf", {"path": "/"})
        assert "not registered" in out.lower() or "Sandbox" in out

    def test_openai_defs_shape(self):
        defs = get_openai_tool_defs(["calculator"])
        assert len(defs) == 1
        assert defs[0]["type"] == "function"
        assert defs[0]["function"]["name"] == "calculator"

    def test_resolve_tools_for_suite(self):
        tools = resolve_tools_for_suite(["calculator", "web_search"])
        names = {t["function"]["name"] for t in tools}
        assert "calculator" in names
        assert "web_search" in names
        assert all(callable(t.get("fn")) or t.get("fn") is None for t in tools)

    def test_builtin_registry_non_empty(self):
        assert len(BUILTIN_TOOLS) >= 3
