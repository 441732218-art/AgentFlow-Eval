# (c) 2026 AgentFlow-Eval
"""Cache key builders and TTL constants for AgentFlow-Eval."""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class CacheTTL(IntEnum):
    """TTL seconds for core cache scenarios."""

    TASK_DETAIL = 300  # 5 min — active invalidation on mutate
    DASHBOARD = 60  # 1 min — short-lived stats
    TASK_LIST = 30  # 30 s — version-dependent invalidation
    EVAL_RESULT = 3600  # 1 h — versioned by content stamp
    SETTINGS = 600  # 10 min — manual / config refresh
    DEFAULT = 300


PREFIX = "af"  # AgentFlow namespace


def cache_key(*parts: Any) -> str:
    """Build a colon-separated cache key under the app prefix.

    Example: ``cache_key("task", "detail", task_id)`` → ``af:task:detail:<id>``.
    """
    clean = [str(p).replace(" ", "_") for p in parts if p is not None and str(p) != ""]
    return ":".join([PREFIX, *clean])


def task_detail_key(task_id: str) -> str:
    return cache_key("task", "detail", task_id)


def task_list_version_key(actor: str) -> str:
    """Monotonic version for an actor's list cache (dependency invalidation)."""
    return cache_key("task", "list_ver", actor or "anonymous")


def task_list_key(
    actor: str,
    version: str | int,
    *,
    page: int,
    page_size: int,
    status: str | None,
    include_archived: bool,
) -> str:
    st = status or "all"
    arch = "1" if include_archived else "0"
    return cache_key(
        "task",
        "list",
        actor or "anonymous",
        version,
        page,
        page_size,
        st,
        arch,
    )


def dashboard_key(actor: str) -> str:
    return cache_key("dashboard", "stats", actor or "anonymous")


def eval_result_key(trace_id: str, version: str) -> str:
    """Versioned evaluation/judge result key."""
    return cache_key("eval", "result", trace_id, version)


def settings_public_key() -> str:
    return cache_key("settings", "public")


def report_key(task_id: str) -> str:
    return cache_key("report", task_id)
