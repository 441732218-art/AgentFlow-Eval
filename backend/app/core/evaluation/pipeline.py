# (c) 2026 AgentFlow-Eval
"""评测流水线聚合纯函数（无 DB/Celery 副作用）。"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def map_agent_status_to_trace(agent_status: str) -> str:
    """Map runner status to trace status (``success`` or ``failed``)."""
    status_map = {
        "success": "success",
        "max_iterations_reached": "failed",
        "failed": "failed",
    }
    return status_map.get(agent_status or "", "failed")


def normalize_judge_result(judge_result: Any) -> dict[str, Any]:
    """Normalize LLMJudge output to dict with scores, total, reason, token_cost."""
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
    """按 trace_id 和 status 拆分成功/失败套件。"""
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
    """Derive overall status: ``completed``, ``partial``, or ``failed``."""
    if failed_count and not successful_count:
        return "failed"
    if failed_count:
        return "partial"
    return "completed"


def aggregate_pipeline_results(
    suite_results: Sequence[dict[str, Any] | None] | None,
    judge_results: Sequence[dict[str, Any] | None] | None,
) -> dict[str, Any]:
    """Aggregate suite and judge outputs into a pipeline summary dict."""
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
        {dim: round(sum(vals) / len(vals), 1) for dim, vals in dimension_scores.items()}
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


def empty_pipeline_result(
    task_id: str, message: str = "No test suites found."
) -> dict[str, Any]:
    """Build a completed empty-suite pipeline payload."""
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
    """Build a failed pipeline payload for orchestration errors."""
    return {
        "task_id": task_id,
        "status": "failed",
        "error_message": error,
        "total_suites": 0,
        "completed_suites": 0,
        "failed_suites": 0,
        "average_score": 0.0,
    }
