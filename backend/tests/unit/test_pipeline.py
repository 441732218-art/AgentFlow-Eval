# (c) 2026 AgentFlow-Eval
"""Unit tests for pure evaluation pipeline helpers."""

from __future__ import annotations

from types import SimpleNamespace

from app.core.evaluation.pipeline import (
    aggregate_pipeline_results,
    determine_overall_status,
    empty_pipeline_result,
    failed_pipeline_result,
    map_agent_status_to_trace,
    normalize_judge_result,
    partition_suite_results,
)


class TestMapAgentStatus:
    def test_success(self) -> None:
        assert map_agent_status_to_trace("success") == "success"

    def test_max_iterations(self) -> None:
        assert map_agent_status_to_trace("max_iterations_reached") == "failed"

    def test_unknown(self) -> None:
        assert map_agent_status_to_trace("weird") == "failed"


class TestNormalizeJudgeResult:
    def test_dict(self) -> None:
        raw = {
            "scores": {"tool_accuracy": 40.0},
            "total": 90.0,
            "reason": "ok",
            "token_cost": 12,
        }
        out = normalize_judge_result(raw)
        assert out["total"] == 90.0
        assert out["token_cost"] == 12
        assert out["scores"]["tool_accuracy"] == 40.0

    def test_object(self) -> None:
        obj = SimpleNamespace(
            scores={"answer_correctness": 30.0},
            total=70.0,
            reason="obj",
            token_cost=3,
        )
        out = normalize_judge_result(obj)
        assert out["total"] == 70.0
        assert out["reason"] == "obj"
        assert out["token_cost"] == 3


class TestPartitionAndStatus:
    def test_partition(self) -> None:
        results = [
            {"trace_id": "t1", "status": "success"},
            {"trace_id": None, "status": "failed"},
            {"trace_id": "t2", "status": "failed"},
            None,
        ]
        ok, bad = partition_suite_results(results)
        assert len(ok) == 1
        assert len(bad) == 3

    def test_overall_completed(self) -> None:
        assert determine_overall_status(2, 0) == "completed"

    def test_overall_partial(self) -> None:
        assert determine_overall_status(1, 1) == "partial"

    def test_overall_failed(self) -> None:
        assert determine_overall_status(0, 2) == "failed"


class TestAggregate:
    def test_aggregate_scores(self) -> None:
        suites = [
            {"trace_id": "a", "status": "success", "total_tokens": 10, "response_time_ms": 100},
            {"trace_id": "b", "status": "success", "total_tokens": 20, "response_time_ms": 200},
        ]
        judges = [
            {
                "total": 80.0,
                "token_cost": 5,
                "scores": {"tool_accuracy": 40.0, "answer_correctness": 40.0},
            },
            {
                "total": 90.0,
                "token_cost": 7,
                "scores": {"tool_accuracy": 40.0, "answer_correctness": 30.0},
            },
        ]
        summary = aggregate_pipeline_results(suites, judges)
        assert summary["completed_suites"] == 2
        assert summary["failed_suites"] == 0
        assert summary["average_score"] == 85.0
        assert summary["dimension_scores"]["tool_accuracy"] == 40.0
        assert summary["dimension_scores"]["answer_correctness"] == 35.0
        assert summary["total_tokens"] == 10 + 20 + 5 + 7
        assert summary["total_time_ms"] == 300
        assert summary["overall_status"] == "completed"

    def test_aggregate_all_failed(self) -> None:
        suites = [{"trace_id": None, "status": "failed"}, None]
        summary = aggregate_pipeline_results(suites, [None, {"total": 0}])
        assert summary["overall_status"] == "failed"
        assert summary["average_score"] == 0.0
        assert summary["completed_suites"] == 0

    def test_empty_and_failed_helpers(self) -> None:
        empty = empty_pipeline_result("tid")
        assert empty["status"] == "completed"
        assert empty["total_suites"] == 0
        failed = failed_pipeline_result("tid", "boom")
        assert failed["status"] == "failed"
        assert "boom" in failed["error_message"]
