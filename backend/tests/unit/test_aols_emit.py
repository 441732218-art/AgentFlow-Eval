# (c) 2026 AgentFlow-Eval
"""Phase 3 AOLS emit helpers — loop detection, step mapping, tool/llm events."""

from __future__ import annotations

from app.core.observability.aols.emit import (
    FINAL_ANSWER,
    THOUGHT,
    TOOL_CALL,
    detect_and_emit_loop,
    elapsed_ms,
    emit_agent,
    emit_evaluation,
    emit_llm,
    emit_tool,
    map_step_type,
    new_execution_id,
    worker_meta,
)
from app.core.observability.aols.events import LogEvent


class TestMapStepType:
    def test_thought(self):
        assert map_step_type(thought="reason") == THOUGHT

    def test_tool_call(self):
        assert map_step_type(action="web_search", has_tool=True) == TOOL_CALL

    def test_final(self):
        assert map_step_type(action="final_answer", is_final=True) == FINAL_ANSWER


class TestLoopDetection:
    def test_detects_repeated_tool_input(self):
        steps = [
            {"action": "search", "action_input": '{"q":"x"}'},
            {"action": "search", "action_input": '{"q":"x"}'},
            {"action": "search", "action_input": '{"q":"x"}'},
        ]
        assert detect_and_emit_loop(steps, execution_id="e1", min_repeats=2) is True

    def test_no_loop_on_diverse_actions(self):
        steps = [
            {"action": "a", "action_input": "1"},
            {"action": "b", "action_input": "2"},
        ]
        assert detect_and_emit_loop(steps, min_repeats=2) is False


class TestEmitSafe:
    def test_emit_functions_do_not_raise(self):
        emit_evaluation(LogEvent.EVALUATION_STARTED, task_id="t1")
        emit_agent(LogEvent.AGENT_STARTED, execution_id="e1", agent_id="react")
        emit_agent(LogEvent.AGENT_COMPLETED, execution_id="e1", status="success")
        emit_llm(
            LogEvent.LLM_COMPLETED,
            model="gpt-4o-mini",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            latency_ms=100,
        )
        emit_tool(
            LogEvent.TOOL_COMPLETED,
            tool_name="calculator",
            latency_ms=3,
            success=True,
            input_data={"expr": "1+1"},
            output_data="2",
        )
        emit_tool(
            LogEvent.TOOL_TIMEOUT,
            tool_name="slow",
            latency_ms=3000,
            success=False,
            error_message="timeout",
        )
        assert len(new_execution_id()) == 16
        assert elapsed_ms(__import__("time").monotonic() - 0.01) >= 0

    def test_worker_meta_empty_without_task(self):
        assert worker_meta(None) == {}
