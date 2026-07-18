# (c) 2026 AgentFlow-Eval
"""Cache warm-up for hot keys after process start."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def warm_cache(*, actor: str = "anonymous", limit: int = 20) -> dict[str, Any]:
    """Preload public settings, dashboard stats, and recent task list for ``actor``.

    Safe to call when Redis is down (operations no-op / degrade).

    Returns:
        Summary dict with keys warmed and any errors.
    """
    from app.core.cache.client import get_cache
    from app.core.cache.keys import (
        CacheTTL,
        dashboard_key,
        settings_public_key,
        task_list_key,
        task_list_version_key,
    )
    from app.core.dependencies import async_session_factory

    cache = get_cache()
    warmed: list[str] = []
    errors: list[str] = []

    # 1) Settings
    try:
        from app.api.v1.endpoints.settings import get_public_settings

        data = await get_public_settings()
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        key = settings_public_key()
        await cache.set(key, payload, ttl=int(CacheTTL.SETTINGS))
        warmed.append(key)
    except Exception as exc:
        errors.append(f"settings: {exc}")

    # 2) Dashboard + recent tasks (DB)
    try:
        from app.core.cache.services import build_dashboard_stats, serialize_task_list

        async with async_session_factory() as session:
            stats = await build_dashboard_stats(session, actor=actor)
            dkey = dashboard_key(actor)
            await cache.set(dkey, stats, ttl=int(CacheTTL.DASHBOARD))
            warmed.append(dkey)

            list_payload = await serialize_task_list(
                session,
                actor=actor,
                role=None,
                page=1,
                page_size=min(limit, 20),
                status=None,
                include_archived=False,
            )
            ver = await cache.get(task_list_version_key(actor)) or 0
            lkey = task_list_key(
                actor,
                ver,
                page=1,
                page_size=min(limit, 20),
                status=None,
                include_archived=False,
            )
            await cache.set(lkey, list_payload, ttl=int(CacheTTL.TASK_LIST))
            warmed.append(lkey)
    except Exception as exc:
        errors.append(f"dashboard/tasks: {exc}")

    logger.info("cache warmup complete warmed=%d errors=%d", len(warmed), len(errors))
    return {"warmed": warmed, "errors": errors, "count": len(warmed)}
