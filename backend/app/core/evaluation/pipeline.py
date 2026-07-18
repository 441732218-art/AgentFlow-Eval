# (c) 2026 AgentFlow-Eval
"""Pure evaluation pipeline helpers — no DB / Celery side effects.

These functions are extracted from celery task orchestration so unit tests
can cover aggregation and status logic without spinning up workers.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def map_agent_status_to_trace(agent_status: str) -> str:
    """Map OpenAIReActRunner status string to TraceStatus value.

    Args:
        agent_status: Runner result status (e.g. ``success``, ``failed``).

    Returns:
        Trace status value string: ``success`` or ``failed``.
    """
    status_map = {
        "success": "success",
        "max_iterations_reached": "failed",
        "failed": "failed",
    }
    return status_map.get(agent_status or "", "failed")


def normalize_judge_result(judge_result: Any) -> dict[str, Any]:
    """Normalize LLMJudge output (dict or object) to a plain dict.

    Args:
        judge_result: Dict-like or attribute-bearing judge response.

    Returns:
        Dict with keys: scores, total, reason, token_cost.
    """
    if isinstance(judge_result, Mapping):
        scores = dict(judge_result.get("scores") or {})
        total = float(judge_result.get("total", 0.0) or 0.0)
        reason = str(judge_result.get("reason", "") or "")
        token_cost = int(judge_result.get("token_cost", 0) or 0)
    else:
        scores = dict(getattr(judge_result, "scores", None) or {})
        total = float(getattr(judge_result, "total", 0.0) or 0.0)
        reason = str(getattr(judge_result, "reason", "") or "")
        token_cost = int(getattr(judge_result, "token_cost", 0) or 0)

    return {
        "scores": scores,
        "total": total,
        "reason": reason,
        "token_cost": token_cost,
    }


def partition_suite_results(
    suite_results: Sequence[dict[str, Any] | None] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any] | None]]:
    """Split suite execution results into successful vs failed.

    A suite is successful when it has a non-empty ``trace_id`` and status
    is not ``failed``.

    Args:
        suite_results: Raw results from ``run_single_test_suite`` group.

    Returns:
        (successful_suites, failed_suites) — failed may contain None entries.
    """
    results = list(suite_results or [])
    successful: list[dict[str, Any]] = []
    failed: list[dict[str, Any] | None] = []

    for r in results:
        if r and r.get("trace_id") and r.get("status") != "failed":
            successful.append(r)
        else:
            failed.append(r)

    return successful, failed


def determine_overall_status(
    successful_count: int,
    failed_count: int,
) -> str:
    """Derive pipeline overall status from suite success/failure counts.

    Args:
        successful_count: Number of suites that produced a usable trace.
        failed_count: Number of suites that failed.

    Returns:
        One of ``completed``, ``partial``, ``failed``.
    """
    if failed_count and not successful_count:
        return "failed"
    if failed_count:
        return "partial"
    return "completed"


def aggregate_pipeline_results(
    suite_results: Sequence[dict[str, Any] | None] | None,
    judge_results: Sequence[dict[str, Any] | None] | None,
) -> dict[str, Any]:
    """Aggregate suite + judge outputs into a pipeline summary.

    Args:
        suite_results: Per-suite execution results.
        judge_results: Per-trace judgment results.

    Returns:
        Dict with average_score, dimension_scores, total_tokens, total_time_ms,
        completed_suites, failed_suites, overall_status.
    """
    successful, failed = partition_suite_results(suite_results)
    judges = [j for j in (judge_results or []) if j]

    total_score = 0.0
    score_count = 0
    dimension_scores: dict[str, list[float]] = {}
    total_tokens = 0
    total_time_ms = 0

    for jr in judges:
        total_score += float(jr.get("total", 0.0) or 0.0)
        score_count += 1
        total_tokens += int(jr.get("token_cost", 0) or 0)
        for dim, val in (jr.get("scores") or {}).items():
            dimension_scores.setdefault(str(dim), []).append(float(val))

    for s_result in suite_results or []:
        if not s_result:
            continue
        total_tokens += int(s_result.get("total_tokens", 0) or 0)
        total_time_ms += int(s_result.get("response_time_ms", 0) or 0)

    avg_score = round(total_score / score_count, 1) if score_count else 0.0
    avg_dim_scores = (
        {
            dim: round(sum(vals) / len(vals), 1)
            for dim, vals in dimension_scores.items()
        }
        if dimension_scores
        else {}
    )

    overall = determine_overall_status(len(successful), len(failed))

    return {
        "completed_suites": len(successful),
        "failed_suites": len(failed),
        "average_score": avg_score,
        "dimension_scores": avg_dim_scores,
        "total_tokens": total_tokens,
        "total_time_ms": total_time_ms,
        "overall_status": overall,
        "score_count": score_count,
    }


def empty_pipeline_result(task_id: str, message: str = "No test suites found.") -> dict[str, Any]:
    """Build a completed empty-suite pipeline payload.

    Args:
        task_id: Task identifier.
        message: Human-readable note.

    Returns:
        Standard pipeline result dict with zero suites.
    """
    return {
        "task_id": task_id,
        "status": "completed",
        "total_suites": 0,
        "completed_suites": 0,
        "failed_suites": 0,
        "average_score": 0.0,
        "message": message,
    }


def failed_pipeline_result(task_id: str, error: str) -> dict[str, Any]:
    """Build a failed pipeline payload for orchestration errors.

    Args:
        task_id: Task identifier.
        error: Error message.

    Returns:
        Standard failure result dict.
    """
    return {
        "task_id": task_id,
        "status": "failed",
        "error_message": error,
        "total_suites": 0,
        "completed_suites": 0,
        "failed_suites": 0,
        "average_score": 0.0,
    }
