# (c) 2026 AgentFlow-Eval
"""Experiment comparison helpers — pure aggregation over report-like data."""

from __future__ import annotations

from typing import Any


def aggregate_task_scores(
    suite_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-suite score data into task-level averages.

    Args:
        suite_rows: Each item may contain ``traces`` list with ``scores`` dicts
            and ``total_tokens`` / ``response_time_ms``.

    Returns:
        Dict with average_score, dimension_scores, total_tokens, total_time_ms,
        scored_traces, suite_count.
    """
    dimension_scores: dict[str, list[float]] = {}
    total_tokens = 0
    total_time_ms = 0
    scored_traces = 0
    per_trace_totals: list[float] = []

    for suite in suite_rows:
        for trace in suite.get("traces") or []:
            total_tokens += int(trace.get("total_tokens") or 0)
            total_time_ms += int(trace.get("response_time_ms") or 0)
            scores = trace.get("scores") or {}
            if not scores:
                continue
            scored_traces += 1
            # Prefer explicit total; else sum dimension scores
            if "total" in scores:
                per_trace_totals.append(float(scores["total"]))
            else:
                per_trace_totals.append(sum(float(v) for v in scores.values()))
            for dim, val in scores.items():
                if dim == "total":
                    continue
                dimension_scores.setdefault(str(dim), []).append(float(val))

    avg_dims = {
        dim: round(sum(vals) / len(vals), 1)
        for dim, vals in dimension_scores.items()
        if vals
    }
    avg_score = (
        round(sum(per_trace_totals) / len(per_trace_totals), 1)
        if per_trace_totals
        else 0.0
    )

    return {
        "average_score": avg_score,
        "dimension_scores": avg_dims,
        "total_tokens": total_tokens,
        "total_time_ms": total_time_ms,
        "scored_traces": scored_traces,
        "suite_count": len(suite_rows),
    }


def pick_best_label(runs: list[dict[str, Any]]) -> str | None:
    """Return label of the run with highest average_score (stable tie-break)."""
    if not runs:
        return None
    ranked = sorted(
        runs,
        key=lambda r: (-float(r.get("average_score") or 0.0), str(r.get("label") or "")),
    )
    return str(ranked[0].get("label") or "") or None


def deltas_vs_best(runs: list[dict[str, Any]], best_label: str | None) -> dict[str, float]:
    """Map label -> average_score - best_score."""
    if not runs or not best_label:
        return {}
    best_score = 0.0
    for r in runs:
        if r.get("label") == best_label:
            best_score = float(r.get("average_score") or 0.0)
            break
    return {
        str(r.get("label")): round(float(r.get("average_score") or 0.0) - best_score, 1)
        for r in runs
        if r.get("label") is not None
    }
