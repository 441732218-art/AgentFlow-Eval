# (c) 2026 AgentFlow-Eval
"""Safe structured event emitters for Agent / LLM / Tool / Evaluation (Phase 3)."""

from __future__ import annotations

import time
import uuid
from collections import Counter
from typing import Any

from app.core.observability.aols.events import LogEvent
from app.core.observability.aols.logger import get_logger
from app.core.observability.aols.redaction import redact_mapping, redact_value

log = get_logger("app.aols")

# Step type constants (wire uppercase)
THOUGHT = "THOUGHT"
ACTION = "ACTION"
TOOL_CALL = "TOOL_CALL"
OBSERVATION = "OBSERVATION"
FINAL_ANSWER = "FINAL_ANSWER"
JUDGE = "JUDGE"


def _safe_emit(event: str | LogEvent, level: str = "info", **fields: Any) -> None:
    """Never raise — observability must not break the pipeline.

    Dual path: structlog (stdout/file) + optional agent_logs DB sink.
    """
    event_name = str(event)
    payload = {k: v for k, v in fields.items() if v is not None}
    try:
        fn = getattr(log, level, None) or log.info
        fn(event_name, **payload)
    except Exception:
        try:
            logging_fallback = __import__("logging").getLogger("app.aols")
            logging_fallback.info("%s %s", event_name, payload)
        except Exception:
            pass

    # Durable sink (best-effort)
    try:
        from app.core.observability.aols.context import get_bound_context
        from app.core.observability.aols.sinks.db import enqueue_agent_log
        from app.core.observability.tracing import get_trace_id

        ctx = get_bound_context()
        tid = (
            payload.get("trace_id")
            or payload.get("request_id")
            or ctx.get("trace_id")
            or ctx.get("request_id")
            or get_trace_id()
            or None
        )
        task_id = payload.get("task_id") or ctx.get("task_id")
        # Nested agent_context.task_id
        ac = payload.get("agent_context")
        if not task_id and isinstance(ac, dict):
            task_id = ac.get("task_id")

        envelope = {
            "event": event_name,
            "level": level,
            **payload,
        }
        if tid:
            envelope.setdefault("trace_id", tid)
        if task_id:
            envelope.setdefault("task_id", task_id)
        # Merge bound context (already redacted on log path; re-redact payload keys)
        for k, v in ctx.items():
            envelope.setdefault(k, v)

        enqueue_agent_log(
            event=event_name,
            level=level,
            trace_id=str(tid) if tid else None,
            task_id=str(task_id) if task_id else None,
            payload=redact_mapping(envelope),
        )
    except Exception:
        pass


def worker_meta(celery_task: Any | None = None) -> dict[str, Any]:
    """Extract Celery worker / retry metadata when available."""
    meta: dict[str, Any] = {}
    if celery_task is None:
        return meta
    try:
        meta["retry_count"] = int(getattr(celery_task, "request", None).retries or 0)
    except Exception:
        pass
    try:
        meta["celery_task_id"] = str(getattr(celery_task, "request", None).id or "")
    except Exception:
        pass
    try:
        meta["worker_name"] = str(
            getattr(getattr(celery_task, "request", None), "hostname", "") or ""
        )
    except Exception:
        pass
    return {k: v for k, v in meta.items() if v not in ("", None)}


def map_step_type(
    *,
    thought: str = "",
    action: str = "",
    observation: str = "",
    is_final: bool = False,
    has_tool: bool = False,
) -> str:
    if is_final or (action or "").lower() in {"final_answer", "final answer"}:
        return FINAL_ANSWER
    if has_tool or (action and action.lower() not in {"", "final_answer"}):
        return TOOL_CALL if has_tool or action else ACTION
    if observation and not thought and not action:
        return OBSERVATION
    if thought:
        return THOUGHT
    if action:
        return ACTION
    return THOUGHT


def emit_evaluation(
    event: LogEvent,
    *,
    task_id: str,
    status: str | None = None,
    duration_ms: int | None = None,
    total_tokens: int | None = None,
    average_score: float | None = None,
    celery_task: Any | None = None,
    **extra: Any,
) -> None:
    _safe_emit(
        event,
        level="error" if event == LogEvent.EVALUATION_FAILED else "info",
        task_id=task_id,
        status=status,
        duration_ms=duration_ms,
        total_tokens=total_tokens,
        average_score=average_score,
        **worker_meta(celery_task),
        **extra,
    )


def emit_agent(
    event: LogEvent,
    *,
    task_id: str | None = None,
    execution_id: str | None = None,
    agent_id: str | None = None,
    agent_version: str | None = None,
    model: str | None = None,
    duration_ms: int | None = None,
    total_tokens: int | None = None,
    status: str | None = None,
    error_message: str | None = None,
    **extra: Any,
) -> None:
    agent_context = {
        k: v
        for k, v in {
            "task_id": task_id,
            "execution_id": execution_id,
            "agent_id": agent_id,
            "agent_version": agent_version,
        }.items()
        if v
    }
    level = "error" if event in (LogEvent.AGENT_FAILED,) else "info"
    _safe_emit(
        event,
        level=level,
        agent_context=agent_context or None,
        task_id=task_id,
        model=model,
        duration_ms=duration_ms,
        total_tokens=total_tokens,
        status=status,
        error_message=error_message,
        **extra,
    )


def emit_agent_step(
    *,
    step_index: int,
    step_type: str,
    task_id: str | None = None,
    execution_id: str | None = None,
    tokens: int | None = None,
    tool_name: str | None = None,
    latency_ms: int | None = None,
    success: bool = True,
    **extra: Any,
) -> None:
    step_id = f"{execution_id or 'exec'}:{step_index}"
    _safe_emit(
        LogEvent.AGENT_STEP_COMPLETED,
        step_context={
            "step_id": step_id,
            "step_type": step_type,
            "step_index": step_index,
        },
        task_id=task_id,
        execution_id=execution_id,
        tokens=tokens,
        tool_name=tool_name,
        latency_ms=latency_ms,
        success=success,
        **extra,
    )


def emit_llm(
    event: LogEvent,
    *,
    provider: str = "openai",
    model: str | None = None,
    prompt_version: str | None = None,
    temperature: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    latency_ms: int | None = None,
    cost: float | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    task_id: str | None = None,
    **extra: Any,
) -> None:
    level = "error" if event == LogEvent.LLM_FAILED else "info"
    # Derive cost if tokens present
    if cost is None and model and total_tokens is not None:
        try:
            from app.utils.cost import calculate_cost

            # split roughly if only total known
            if input_tokens is not None and output_tokens is not None:
                cost = calculate_cost(model, input_tokens, output_tokens)
            elif total_tokens:
                cost = calculate_cost(model, total_tokens, 0)
        except Exception:
            cost = None
    _safe_emit(
        event,
        level=level,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        temperature=temperature,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        cost=cost,
        error_type=error_type,
        error_message=error_message,
        task_id=task_id,
        **extra,
    )


def emit_tool(
    event: LogEvent,
    *,
    tool_name: str,
    latency_ms: int | None = None,
    success: bool | None = None,
    input_data: Any = None,
    output_data: Any = None,
    error_message: str | None = None,
    **extra: Any,
) -> None:
    level = (
        "error" if event in (LogEvent.TOOL_FAILED, LogEvent.TOOL_TIMEOUT) else "info"
    )
    # Redact tool I/O for safety; truncate
    safe_in = redact_value(input_data, max_str=400) if input_data is not None else None
    safe_out = None
    if output_data is not None:
        out_s = str(output_data)
        if len(out_s) > 400:
            out_s = out_s[:400] + "…[truncated]"
        safe_out = out_s
    _safe_emit(
        event,
        level=level,
        tool_name=tool_name,
        latency_ms=latency_ms,
        success=success,
        input=safe_in,
        output=safe_out,
        error_message=error_message,
        **extra,
    )


def detect_and_emit_loop(
    steps: list[dict[str, Any]],
    *,
    task_id: str | None = None,
    execution_id: str | None = None,
    min_repeats: int = 2,
) -> bool:
    """Heuristic: same tool + input appears >= min_repeats → agent.loop.detected."""
    pairs: list[tuple[str, str]] = []
    for s in steps or []:
        action = str(s.get("action") or s.get("tool_name") or "")
        ain = str(s.get("action_input") or s.get("tool_input") or "")[:120]
        if action and action.lower() not in {"final_answer", ""}:
            pairs.append((action, ain))
    if not pairs:
        return False
    counts = Counter(pairs)
    worst = counts.most_common(1)[0]
    loop_count = worst[1]
    if loop_count < min_repeats:
        return False
    _safe_emit(
        LogEvent.AGENT_LOOP_DETECTED,
        level="warning",
        task_id=task_id,
        execution_id=execution_id,
        loop_count=loop_count,
        tool_name=worst[0][0],
        action_input_preview=worst[0][1],
    )
    return True


def new_execution_id() -> str:
    return uuid.uuid4().hex[:16]


def elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
