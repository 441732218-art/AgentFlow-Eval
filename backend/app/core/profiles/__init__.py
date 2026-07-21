# (c) 2026 AgentFlow-Eval
"""Deploy profiles — bind ports/adapters without rewriting business logic."""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.core.ports.cache import CachePort
from app.core.ports.event_bus import EventBusPort
from app.core.ports.metering import MeteringPort
from app.core.ports.task_queue import TaskQueuePort

logger = logging.getLogger(__name__)

ProfileName = Literal["lite", "private", "saas"]

_queue: TaskQueuePort | None = None
_cache: CachePort | None = None
_bus: EventBusPort | None = None
_meter: MeteringPort | None = None
_profile: str = "private"
_applied: bool = False


def get_task_queue() -> TaskQueuePort:
    global _queue
    if _queue is None:
        apply_profile_from_settings()
    assert _queue is not None
    return _queue


def get_cache_port() -> CachePort:
    global _cache
    if _cache is None:
        apply_profile_from_settings()
    assert _cache is not None
    return _cache


def get_event_bus() -> EventBusPort:
    global _bus
    if _bus is None:
        apply_profile_from_settings()
    assert _bus is not None
    return _bus


def get_meter() -> MeteringPort:
    global _meter
    if _meter is None:
        apply_profile_from_settings()
    assert _meter is not None
    return _meter


def current_profile() -> str:
    return _profile


def bind_ports(
    *,
    queue: TaskQueuePort,
    cache: CachePort,
    bus: EventBusPort,
    meter: MeteringPort,
    profile: str,
) -> None:
    global _queue, _cache, _bus, _meter, _profile, _applied
    _queue = queue
    _cache = cache
    _bus = bus
    _meter = meter
    _profile = profile
    _applied = True


def reset_ports() -> None:
    """Test helper — clear bindings so next get_* re-applies profile."""
    global _queue, _cache, _bus, _meter, _applied
    _queue = None
    _cache = None
    _bus = None
    _meter = None
    _applied = False


def apply_profile(
    profile: str,
    *,
    task_queue_backend: str | None = None,
    billing_enabled: bool = False,
) -> dict[str, Any]:
    """Bind adapters for the given deploy profile.

    ``task_queue_backend`` overrides profile defaults: celery|eager|memory.
    """
    profile = (profile or "private").lower().strip()
    if profile not in {"lite", "private", "saas"}:
        logger.warning("Unknown DEPLOY_PROFILE=%r, falling back to private", profile)
        profile = "private"

    tq = (task_queue_backend or "").lower().strip()

    def _pick_meter() -> MeteringPort:
        if billing_enabled:
            from app.core.adapters.metering.sqlalchemy_meter import SqlAlchemyMeter

            return SqlAlchemyMeter()
        from app.core.adapters.metering.noop import NoopMeter

        return NoopMeter()

    if profile == "lite":
        from app.core.adapters.queue.eager_queue import EagerTaskQueue
        from app.core.adapters.queue.memory_queue import MemoryTaskQueue
        from app.core.adapters.cache.memory_only import MemoryOnlyCacheAdapter
        from app.core.adapters.bus.inprocess import InProcessEventBus

        if tq == "memory":
            queue: TaskQueuePort = MemoryTaskQueue()
        elif tq == "celery":
            from app.core.adapters.queue.celery_queue import CeleryTaskQueue

            queue = CeleryTaskQueue()
        else:
            queue = EagerTaskQueue()  # default lite
        cache: CachePort = MemoryOnlyCacheAdapter()
        bus: EventBusPort = InProcessEventBus()
        meter = _pick_meter()
    elif profile == "saas":
        from app.core.adapters.queue.celery_queue import CeleryTaskQueue
        from app.core.adapters.queue.eager_queue import EagerTaskQueue
        from app.core.adapters.queue.memory_queue import MemoryTaskQueue
        from app.core.adapters.cache.redis_l2 import RedisL2CacheAdapter
        from app.core.adapters.bus.redis_pubsub import RedisEventBus

        if tq == "eager":
            queue = EagerTaskQueue()
        elif tq == "memory":
            queue = MemoryTaskQueue()
        else:
            queue = CeleryTaskQueue()
        cache = RedisL2CacheAdapter()
        bus = RedisEventBus()
        # SaaS defaults to SQL meter when billing flag on
        meter = _pick_meter() if billing_enabled else _pick_meter()
    else:  # private
        from app.core.adapters.queue.celery_queue import CeleryTaskQueue
        from app.core.adapters.queue.eager_queue import EagerTaskQueue
        from app.core.adapters.queue.memory_queue import MemoryTaskQueue
        from app.core.adapters.cache.redis_l2 import RedisL2CacheAdapter
        from app.core.adapters.bus.redis_pubsub import RedisEventBus

        if tq == "eager":
            queue = EagerTaskQueue()
        elif tq == "memory":
            queue = MemoryTaskQueue()
        else:
            queue = CeleryTaskQueue()
        cache = RedisL2CacheAdapter()
        bus = RedisEventBus()
        meter = _pick_meter()

    bind_ports(queue=queue, cache=cache, bus=bus, meter=meter, profile=profile)
    summary = {
        "profile": profile,
        "task_queue": queue.backend_name,
        "cache": cache.backend_name,
        "event_bus": bus.backend_name,
        "metering": meter.backend_name,
        "eager": queue.is_eager(),
    }
    logger.info("Deploy profile applied: %s", summary)
    return summary


def apply_profile_from_settings() -> dict[str, Any]:
    """Read ``app.config.settings`` and apply profile (idempotent-ish)."""
    from app.config import settings

    profile = getattr(settings, "DEPLOY_PROFILE", None) or "private"
    # Auto-lite when eager + sqlite and profile not forced
    if str(profile).lower() == "auto":
        db = str(getattr(settings, "DATABASE_URL", "") or "")
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and "sqlite" in db:
            profile = "lite"
        else:
            profile = "private"

    tq = getattr(settings, "TASK_QUEUE_BACKEND", None) or ""
    # If private/saas but CELERY_TASK_ALWAYS_EAGER, prefer eager queue when backend empty
    if not tq and getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        if str(profile).lower() in {"private", "saas", "auto"}:
            tq = "eager"

    billing = bool(getattr(settings, "BILLING_ENABLED", False))
    return apply_profile(
        str(profile), task_queue_backend=tq or None, billing_enabled=billing
    )


def profile_status() -> dict[str, Any]:
    q = get_task_queue()
    return {
        "profile": current_profile(),
        "task_queue": q.backend_name,
        "cache": get_cache_port().backend_name,
        "event_bus": get_event_bus().backend_name,
        "metering": get_meter().backend_name,
        "eager": q.is_eager(),
        "applied": _applied,
    }
