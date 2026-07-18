# (c) 2026 AgentFlow-Eval
"""Tests for experiment comparison helpers."""

from app.core.evaluation.compare import (
    aggregate_task_scores,
    deltas_vs_best,
    pick_best_label,
)


def test_aggregate_task_scores() -> None:
    suites = [
        {
            "traces": [
                {
                    "total_tokens": 10,
                    "response_time_ms": 100,
                    "scores": {
                        "tool_accuracy": 40.0,
                        "answer_correctness": 30.0,
                        "total": 90.0,
                    },
                }
            ]
        },
        {
            "traces": [
                {
                    "total_tokens": 20,
                    "response_time_ms": 200,
                    "scores": {
                        "tool_accuracy": 40.0,
                        "answer_correctness": 40.0,
                        "total": 100.0,
                    },
                }
            ]
        },
    ]
    agg = aggregate_task_scores(suites)
    assert agg["average_score"] == 95.0
    assert agg["dimension_scores"]["tool_accuracy"] == 40.0
    assert agg["dimension_scores"]["answer_correctness"] == 35.0
    assert agg["total_tokens"] == 30
    assert agg["scored_traces"] == 2


def test_pick_best_and_deltas() -> None:
    runs = [
        {"label": "a", "average_score": 80.0},
        {"label": "b", "average_score": 95.0},
        {"label": "c", "average_score": 95.0},
    ]
    best = pick_best_label(runs)
    # tie-break by label ascending after score desc → b before c
    assert best == "b"
    deltas = deltas_vs_best(runs, best)
    assert deltas["b"] == 0.0
    assert deltas["a"] == -15.0


def test_empty() -> None:
    assert pick_best_label([]) is None
    assert deltas_vs_best([], None) == {}
    agg = aggregate_task_scores([])
    assert agg["average_score"] == 0.0
