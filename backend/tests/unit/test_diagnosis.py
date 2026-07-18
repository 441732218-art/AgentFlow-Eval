# (c) 2026 AgentFlow-Eval
"""Unit tests for diagnosis engine heuristics."""

from __future__ import annotations

from types import SimpleNamespace

from app.core.diagnosis.engine import (
    ISSUE_AGENT_LOOP,
    ISSUE_NONE,
    ISSUE_TOOL_FAILURE,
    diagnose_from_traces,
)


def _trace(
    *,
    steps=None,
    status="success",
    tokens=100,
    cost=0.01,
    prompt_version="v1",
    metric_scores=None,
):
    return SimpleNamespace(
        id="t1",
        steps=steps or [],
        status=SimpleNamespace(value=status),
        total_tokens=tokens,
        response_time_ms=1200,
        cost=cost,
        prompt_version=prompt_version,
        metric_scores=metric_scores or [],
    )


def test_healthy_when_no_issues():
    t = _trace(steps=[{"type": "final_answer", "content": "ok"}])
    result = diagnose_from_traces(task=None, traces=[t])
    assert result["issue"] == ISSUE_NONE
    assert result["confidence"] >= 0.9
    assert "suggestion" in result


def test_agent_loop_detection():
    steps = []
    for _ in range(3):
        steps.append(
            {
                "type": "action",
                "tool_name": "search",
                "tool_input": '{"q":"same"}',
            }
        )
        steps.append({"type": "observation", "content": "result"})
    t = _trace(steps=steps, status="failed")
    result = diagnose_from_traces(task=None, traces=[t])
    assert result["issue"] == ISSUE_AGENT_LOOP
    assert result["topology"]["edges"]


def test_tool_failure_from_observation_error():
    t = _trace(
        steps=[
            {"type": "action", "tool_name": "api", "tool_input": "{}"},
            {"type": "observation", "content": "Error: timeout connecting to API"},
        ],
        status="failed",
    )
    result = diagnose_from_traces(task=None, traces=[t])
    assert result["issue"] == ISSUE_TOOL_FAILURE
    assert "root_cause" in result
