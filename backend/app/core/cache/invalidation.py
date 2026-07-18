# (c) 2026 AgentFlow-Eval
"""Cache invalidation helpers for mutations."""

from __future__ import annotations

import logging

from app.core.cache.client import get_cache
from app.core.cache.keys import (
    PREFIX,
    dashboard_key,
    report_key,
    settings_public_key,
    task_detail_key,
    task_list_version_key,
)

logger = logging.getLogger(__name__)


async def invalidate_task(task_id: str, *, actor: str | None = None) -> None:
    """Invalidate task detail + related list/dashboard/report caches."""
    cache = get_cache()
    await cache.delete(task_detail_key(task_id))
    await cache.delete(report_key(task_id))
    if actor:
        await invalidate_task_lists(actor)
        await invalidate_dashboard(actor)
    else:
        # Broad list invalidation via version keys is actor-scoped; bump anonymous too
        await invalidate_task_lists("anonymous")
        await invalidate_dashboard("anonymous")
    logger.debug("invalidated task cache task_id=%s", task_id)


async def invalidate_task_lists(actor: str) -> None:
    """Bump list version so existing list keys miss (dependency invalidation)."""
    cache = get_cache()
    ver_key = task_list_version_key(actor)
    await cache.incr(ver_key, ttl=86400)
    # Also drop any residual L1/L2 keys for this actor's lists
    await cache.delete_pattern(f"{PREFIX}:task:list:{actor or 'anonymous'}:*")
    logger.debug("bumped task list version actor=%s", actor)


async def invalidate_dashboard(actor: str) -> None:
    await get_cache().delete(dashboard_key(actor))


async def invalidate_eval(trace_id: str) -> None:
    """Drop all versioned eval keys for a trace."""
    await get_cache().delete_pattern(f"{PREFIX}:eval:result:{trace_id}:*")


async def invalidate_settings() -> None:
    await get_cache().delete(settings_public_key())


async def invalidate_all_task_lists() -> None:
    """Invalidate all task list caches (admin-wide)."""
    await get_cache().delete_pattern(f"{PREFIX}:task:list:*")
    await get_cache().delete_pattern(f"{PREFIX}:task:list_ver:*")
