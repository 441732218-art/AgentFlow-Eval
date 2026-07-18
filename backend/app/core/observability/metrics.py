# (c) 2026 AgentFlow-Eval
"""Prometheus metrics for AgentFlow-Eval.

Core series
-----------
HTTP layer
  - ``agentflow_http_requests_total``
  - ``agentflow_http_request_duration_seconds``

Business layer
  - ``agentflow_tasks_created_total``          labels: tenant, model, runner
  - ``agentflow_evaluations_total``            labels: status, tenant, model, runner
  - ``agentflow_evaluation_duration_seconds`` labels: status, runner
  - ``agentflow_suite_runs_total``            labels: status, runner
  - ``agentflow_suite_run_duration_seconds``  labels: status, runner
  - ``agentflow_judge_evaluations_total``     labels: mode, status
  - ``agentflow_judge_duration_seconds``      labels: mode, status
  - ``agentflow_tokens_total``                labels: stage, model, runner

All record helpers are sync and thread-safe (prometheus_client locks).
They are safe to call from async code without blocking meaningfully.
"""

from __future__ import annotations

import functools
import logging
import re
import time
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

METRICS_PATH = "/metrics"

# ---- Registry (module-level; process-local) ----
REGISTRY = CollectorRegistry(auto_describe=True)

# UUID / numeric id segments → reduce cardinality on HTTP paths
_PATH_ID_RE = re.compile(
    r"(?<=/)"
    r"(?:"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|[0-9a-fA-F]{24,}"
    r"|\d+"
    r")"
    r"(?=/|$)"
)

_HTTP_LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
)
_JOB_LATENCY_BUCKETS = (
    0.1,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
    600.0,
)

# ---- Metric definitions ----
HTTP_REQUESTS = Counter(
    "agentflow_http_requests_total",
    "Total HTTP requests handled by the API",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION = Histogram(
    "agentflow_http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=("method", "path", "status"),
    buckets=_HTTP_LATENCY_BUCKETS,
    registry=REGISTRY,
)

TASKS_CREATED = Counter(
    "agentflow_tasks_created_total",
    "Evaluation tasks created",
    labelnames=("tenant", "model", "runner"),
    registry=REGISTRY,
)

EVALUATIONS = Counter(
    "agentflow_evaluations_total",
    "Full pipeline evaluations finished",
    labelnames=("status", "tenant", "model", "runner"),
    registry=REGISTRY,
)

EVALUATION_DURATION = Histogram(
    "agentflow_evaluation_duration_seconds",
    "Full pipeline wall time in seconds",
    labelnames=("status", "runner"),
    buckets=_JOB_LATENCY_BUCKETS,
    registry=REGISTRY,
)

SUITE_RUNS = Counter(
    "agentflow_suite_runs_total",
    "Single test-suite agent executions",
    labelnames=("status", "runner"),
    registry=REGISTRY,
)

SUITE_RUN_DURATION = Histogram(
    "agentflow_suite_run_duration_seconds",
    "Single suite agent execution time in seconds",
    labelnames=("status", "runner"),
    buckets=_JOB_LATENCY_BUCKETS,
    registry=REGISTRY,
)

JUDGE_EVALUATIONS = Counter(
    "agentflow_judge_evaluations_total",
    "Judge evaluations finished",
    labelnames=("mode", "status"),
    registry=REGISTRY,
)

JUDGE_DURATION = Histogram(
    "agentflow_judge_duration_seconds",
    "Judge evaluation time in seconds",
    labelnames=("mode", "status"),
    buckets=_JOB_LATENCY_BUCKETS,
    registry=REGISTRY,
)

TOKENS = Counter(
    "agentflow_tokens_total",
    "LLM / agent tokens consumed",
    labelnames=("stage", "model", "runner"),
    registry=REGISTRY,
)

# Error topology by pipeline stage (agent | judge | tool | plugin | pipeline)
STAGE_ERRORS = Counter(
    "agentflow_stage_errors_total",
    "Pipeline errors by stage",
    labelnames=("stage", "status"),
    registry=REGISTRY,
)

SLOW_TASKS = Counter(
    "agentflow_slow_tasks_total",
    "Slow task samples recorded",
    labelnames=("stage",),
    registry=REGISTRY,
)

# ---- Resilience ----
RESILIENCE_RETRIES = Counter(
    "agentflow_resilience_retries_total",
    "Retry attempts for protected external calls",
    labelnames=("name",),
    registry=REGISTRY,
)

RESILIENCE_CIRCUIT_CALLS = Counter(
    "agentflow_resilience_circuit_calls_total",
    "Circuit breaker call outcomes",
    labelnames=("name", "result"),
    registry=REGISTRY,
)

RESILIENCE_CIRCUIT_STATE = Counter(
    "agentflow_resilience_circuit_state_transitions_total",
    "Circuit breaker state observations / transitions",
    labelnames=("name", "state"),
    registry=REGISTRY,
)

RESILIENCE_FALLBACKS = Counter(
    "agentflow_resilience_fallbacks_total",
    "Fallback invocations after protected-call failure",
    labelnames=("name", "reason"),
    registry=REGISTRY,
)

RESILIENCE_TIMEOUTS = Counter(
    "agentflow_resilience_timeouts_total",
    "Timeouts on protected external calls",
    labelnames=("name",),
    registry=REGISTRY,
)

# ---- Cache ----
CACHE_HITS = Counter(
    "agentflow_cache_hits_total",
    "Cache hits by layer (l1 memory / l2 redis)",
    labelnames=("layer",),
    registry=REGISTRY,
)
CACHE_MISSES = Counter(
    "agentflow_cache_misses_total",
    "Cache misses (both layers)",
    registry=REGISTRY,
)
CACHE_SETS = Counter(
    "agentflow_cache_sets_total",
    "Cache write operations",
    registry=REGISTRY,
)
CACHE_INVALIDATIONS = Counter(
    "agentflow_cache_invalidations_total",
    "Keys invalidated / deleted from cache",
    registry=REGISTRY,
)

P = ParamSpec("P")
R = TypeVar("R")


def _metrics_enabled() -> bool:
    try:
        from app.config import settings

        return bool(getattr(settings, "METRICS_ENABLED", True))
    except Exception:
        return True


def _label(value: str | None, default: str = "unknown", max_len: int = 64) -> str:
    """Sanitize a label value for Prometheus (avoid empty / huge strings)."""
    text = (value or "").strip() or default
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def normalize_path(path: str) -> str:
    """Collapse dynamic path segments to keep cardinality bounded.

    Args:
        path: Raw request path (e.g. ``/api/v1/tasks/uuid/execute``).

    Returns:
        Normalized path (e.g. ``/api/v1/tasks/{id}/execute``).
    """
    if not path:
        return "/"
    normalized = _PATH_ID_RE.sub("{id}", path)
    # Cap extreme lengths
    if len(normalized) > 120:
        return normalized[:117] + "..."
    return normalized


def extract_model(agent_config: dict[str, Any] | None) -> str:
    """Extract model label from agent_config."""
    cfg = agent_config or {}
    return _label(str(cfg.get("model") or cfg.get("model_name") or "default"))


def extract_runner(agent_config: dict[str, Any] | None) -> str:
    """Extract runner type label from agent_config."""
    cfg = agent_config or {}
    runner = cfg.get("runner") or cfg.get("type") or "openai"
    return _label(str(runner).lower())


def observe_http_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record one HTTP request (count + latency)."""
    if not _metrics_enabled():
        return
    method_l = _label(method.upper(), "GET", max_len=16)
    path_l = normalize_path(path)
    status_l = str(int(status_code))
    try:
        HTTP_REQUESTS.labels(method=method_l, path=path_l, status=status_l).inc()
        HTTP_REQUEST_DURATION.labels(
            method=method_l, path=path_l, status=status_l
        ).observe(max(0.0, float(duration_seconds)))
    except Exception as exc:  # never break request path
        logger.debug("http metrics skipped: %s", exc)


def observe_task_created(
    *,
    tenant: str | None = None,
    agent_config: dict[str, Any] | None = None,
) -> None:
    """Increment task-created counter."""
    if not _metrics_enabled():
        return
    try:
        TASKS_CREATED.labels(
            tenant=_label(tenant, "anonymous"),
            model=extract_model(agent_config),
            runner=extract_runner(agent_config),
        ).inc()
    except Exception as exc:
        logger.debug("task_created metrics skipped: %s", exc)


def observe_evaluation(
    *,
    status: str,
    duration_seconds: float,
    tenant: str | None = None,
    agent_config: dict[str, Any] | None = None,
    total_tokens: int = 0,
) -> None:
    """Record a finished full-pipeline evaluation."""
    if not _metrics_enabled():
        return
    status_l = _label(status, "unknown", max_len=32)
    runner = extract_runner(agent_config)
    model = extract_model(agent_config)
    try:
        EVALUATIONS.labels(
            status=status_l,
            tenant=_label(tenant, "anonymous"),
            model=model,
            runner=runner,
        ).inc()
        EVALUATION_DURATION.labels(status=status_l, runner=runner).observe(
            max(0.0, float(duration_seconds))
        )
        if total_tokens:
            TOKENS.labels(stage="evaluation", model=model, runner=runner).inc(
                max(0, int(total_tokens))
            )
    except Exception as exc:
        logger.debug("evaluation metrics skipped: %s", exc)


def observe_suite_run(
    *,
    status: str,
    duration_seconds: float,
    agent_config: dict[str, Any] | None = None,
    total_tokens: int = 0,
    actor: str | None = None,
    ref_id: str | None = None,
) -> None:
    """Record a single suite (agent) execution."""
    actor_name = (actor or "anonymous").strip() or "anonymous"
    # Slow-task sampling (independent of Prometheus flag)
    try:
        from app.config import settings
        from app.core.observability.slow_tasks import record_slow_task

        thr = float(getattr(settings, "SLOW_TASK_THRESHOLD_SEC", 30.0) or 30.0)
        recorded = record_slow_task(
            stage="agent",
            duration_sec=float(duration_seconds),
            threshold_sec=thr,
            status=status,
            ref_id=ref_id,
            actor=actor_name,
            extra={"runner": extract_runner(agent_config), "actor": actor_name},
        )
        if recorded and _metrics_enabled():
            try:
                SLOW_TASKS.labels(stage="agent").inc()
            except Exception:
                pass
    except Exception:
        pass
    # Meter tokens via port (best-effort) — bind real actor when known
    try:
        if total_tokens:
            from app.core.profiles import get_meter

            get_meter().record(
                actor=actor_name,
                metric="token",
                quantity=float(total_tokens),
                ref_type="suite",
                ref_id=ref_id,
                extra={"stage": "agent"},
            )
    except Exception:
        pass

    if not _metrics_enabled():
        return
    status_l = _label(status, "unknown", max_len=32)
    runner = extract_runner(agent_config)
    model = extract_model(agent_config)
    try:
        SUITE_RUNS.labels(status=status_l, runner=runner).inc()
        SUITE_RUN_DURATION.labels(status=status_l, runner=runner).observe(
            max(0.0, float(duration_seconds))
        )
        if total_tokens:
            TOKENS.labels(stage="agent", model=model, runner=runner).inc(
                max(0, int(total_tokens))
            )
        if status_l in {"failed", "error", "timeout"}:
            STAGE_ERRORS.labels(stage="agent", status=status_l).inc()
    except Exception as exc:
        logger.debug("suite_run metrics skipped: %s", exc)


def observe_judge(
    *,
    mode: str,
    status: str,
    duration_seconds: float,
    token_cost: int = 0,
    agent_config: dict[str, Any] | None = None,
    actor: str | None = None,
    ref_id: str | None = None,
) -> None:
    """Record a judge evaluation."""
    actor_name = (actor or "anonymous").strip() or "anonymous"
    try:
        from app.config import settings
        from app.core.observability.slow_tasks import record_slow_task

        thr = float(getattr(settings, "SLOW_TASK_THRESHOLD_SEC", 30.0) or 30.0)
        recorded = record_slow_task(
            stage="judge",
            duration_sec=float(duration_seconds),
            threshold_sec=thr,
            status=status,
            ref_id=ref_id,
            actor=actor_name,
            extra={"mode": mode, "actor": actor_name},
        )
        if recorded and _metrics_enabled():
            try:
                SLOW_TASKS.labels(stage="judge").inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        from app.core.profiles import get_meter

        get_meter().record(
            actor=actor_name,
            metric="judge",
            quantity=1.0,
            ref_type="judge",
            ref_id=ref_id,
            extra={"mode": mode, "token_cost": token_cost},
        )
        if token_cost:
            get_meter().record(
                actor=actor_name,
                metric="token",
                quantity=float(token_cost),
                ref_type="judge",
                ref_id=ref_id,
            )
    except Exception:
        pass

    if not _metrics_enabled():
        return
    mode_l = _label(mode, "rule_only", max_len=32)
    status_l = _label(status, "ok", max_len=32)
    model = extract_model(agent_config)
    runner = extract_runner(agent_config)
    try:
        JUDGE_EVALUATIONS.labels(mode=mode_l, status=status_l).inc()
        JUDGE_DURATION.labels(mode=mode_l, status=status_l).observe(
            max(0.0, float(duration_seconds))
        )
        if token_cost:
            TOKENS.labels(stage="judge", model=model, runner=runner).inc(
                max(0, int(token_cost))
            )
        if status_l in {"failed", "error"}:
            STAGE_ERRORS.labels(stage="judge", status=status_l).inc()
    except Exception as exc:
        logger.debug("judge metrics skipped: %s", exc)


def observe_stage_error(*, stage: str, status: str = "error") -> None:
    """Increment stage error topology counter (safe no-op if metrics off)."""
    if not _metrics_enabled():
        return
    try:
        STAGE_ERRORS.labels(
            stage=_label(stage, "pipeline", max_len=32),
            status=_label(status, "error", max_len=32),
        ).inc()
    except Exception as exc:
        logger.debug("stage error metrics skipped: %s", exc)


def observe_agent_run(
    *,
    status: str,
    duration_seconds: float,
    agent_config: dict[str, Any] | None = None,
    total_tokens: int = 0,
) -> None:
    """Alias of :func:`observe_suite_run` for agent-level instrumentation."""
    observe_suite_run(
        status=status,
        duration_seconds=duration_seconds,
        agent_config=agent_config,
        total_tokens=total_tokens,
    )


def observe_retry(name: str, *, attempt: int = 1) -> None:
    """Record a retry attempt for a protected call."""
    if not _metrics_enabled():
        return
    try:
        RESILIENCE_RETRIES.labels(name=_label(name, "llm")).inc()
    except Exception as exc:
        logger.debug("retry metrics skipped: %s", exc)


def observe_circuit_call(name: str, result: str) -> None:
    """Record circuit breaker call result (success|failure)."""
    if not _metrics_enabled():
        return
    try:
        RESILIENCE_CIRCUIT_CALLS.labels(
            name=_label(name, "llm"),
            result=_label(result, "unknown", max_len=16),
        ).inc()
    except Exception as exc:
        logger.debug("circuit call metrics skipped: %s", exc)


def observe_circuit_state(name: str, state: str) -> None:
    """Record circuit breaker state transition observation."""
    if not _metrics_enabled():
        return
    try:
        RESILIENCE_CIRCUIT_STATE.labels(
            name=_label(name, "llm"),
            state=_label(state, "closed", max_len=16),
        ).inc()
    except Exception as exc:
        logger.debug("circuit state metrics skipped: %s", exc)


def observe_fallback(name: str, reason: str) -> None:
    """Record a fallback after protected call failure."""
    if not _metrics_enabled():
        return
    try:
        RESILIENCE_FALLBACKS.labels(
            name=_label(name, "llm"),
            reason=_label(reason, "error", max_len=32),
        ).inc()
    except Exception as exc:
        logger.debug("fallback metrics skipped: %s", exc)


def observe_timeout(name: str) -> None:
    """Record a timeout on a protected call."""
    if not _metrics_enabled():
        return
    try:
        RESILIENCE_TIMEOUTS.labels(name=_label(name, "llm")).inc()
    except Exception as exc:
        logger.debug("timeout metrics skipped: %s", exc)


def observe_cache_hit(layer: str = "l2") -> None:
    if not _metrics_enabled():
        return
    try:
        CACHE_HITS.labels(layer=_label(layer, "l2", max_len=8)).inc()
    except Exception as exc:
        logger.debug("cache hit metrics skipped: %s", exc)


def observe_cache_miss() -> None:
    if not _metrics_enabled():
        return
    try:
        CACHE_MISSES.inc()
    except Exception as exc:
        logger.debug("cache miss metrics skipped: %s", exc)


def observe_cache_set() -> None:
    if not _metrics_enabled():
        return
    try:
        CACHE_SETS.inc()
    except Exception as exc:
        logger.debug("cache set metrics skipped: %s", exc)


def observe_cache_invalidate(n: int = 1) -> None:
    if not _metrics_enabled():
        return
    try:
        CACHE_INVALIDATIONS.inc(max(0, int(n)))
    except Exception as exc:
        logger.debug("cache invalidate metrics skipped: %s", exc)


def track_duration(
    metric: str = "evaluation",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """Decorator for async callables: measure wall time and record metrics.

    Args:
        metric: One of ``evaluation``, ``suite``, ``judge``, ``agent``.

    The decorated function may return a dict with optional keys:
    ``status``, ``mode``, ``total_tokens``, ``token_cost``, ``agent_config``,
    ``tenant`` — used as metric labels when present.
    """

    def decorator(
        fn: Callable[P, Awaitable[R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            status = "ok"
            result: R
            try:
                result = await fn(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                elapsed = time.perf_counter() - start
                payload: dict[str, Any] = {}
                # result may not exist if exception before assignment
                if status == "ok":
                    try:
                        maybe = locals().get("result")
                        if isinstance(maybe, dict):
                            payload = maybe
                    except Exception:
                        payload = {}
                _record_from_decorator(metric, elapsed, status, payload)

        return wrapper

    return decorator


def _record_from_decorator(
    metric: str,
    elapsed: float,
    status: str,
    payload: dict[str, Any],
) -> None:
    cfg = payload.get("agent_config") if isinstance(payload.get("agent_config"), dict) else None
    result_status = str(payload.get("status") or status)
    if metric == "evaluation":
        observe_evaluation(
            status=result_status,
            duration_seconds=elapsed,
            tenant=payload.get("tenant"),
            agent_config=cfg,
            total_tokens=int(payload.get("total_tokens") or 0),
        )
    elif metric in {"suite", "agent"}:
        observe_suite_run(
            status=result_status,
            duration_seconds=elapsed,
            agent_config=cfg,
            total_tokens=int(payload.get("total_tokens") or 0),
        )
    elif metric == "judge":
        observe_judge(
            mode=str(payload.get("mode") or "rule_only"),
            status="error" if status == "error" else "ok",
            duration_seconds=elapsed,
            token_cost=int(payload.get("token_cost") or 0),
            agent_config=cfg,
        )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request counts and latencies for all non-metrics routes."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path == METRICS_PATH:
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            observe_http_request(
                method=request.method,
                path=path,
                status_code=status_code,
                duration_seconds=time.perf_counter() - start,
            )


def get_metrics_response() -> Response:
    """Build a Prometheus text exposition response for ``GET /metrics``."""
    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


def render_metrics() -> bytes:
    """Return raw Prometheus exposition bytes (useful in tests)."""
    return generate_latest(REGISTRY)
