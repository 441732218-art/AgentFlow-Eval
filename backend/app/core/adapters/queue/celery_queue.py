# (c) 2026 AgentFlow-Eval
"""Celery-backed TaskQueuePort — default for private/saas profiles."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from app.core.ports.task_queue import EnqueueResult

logger = logging.getLogger(__name__)

# Logical name → Celery task callable (lazy resolved)
_TASK_MAP: dict[str, str] = {
    "run_full_evaluation": "app.core.celery_app.tasks.run_full_evaluation",
    "run_single_test_suite": "app.core.celery_app.tasks.run_single_test_suite",
    "run_judge_evaluation": "app.core.celery_app.tasks.run_judge_evaluation",
}


def _resolve_task(name: str) -> Callable[..., Any]:
    path = _TASK_MAP.get(name) or name
    if ":" in path:
        mod_name, attr = path.rsplit(":", 1)
    elif path.count(".") >= 2:
        mod_name, attr = path.rsplit(".", 1)
    else:
        raise KeyError(f"unknown task: {name}")
    import importlib

    mod = importlib.import_module(mod_name)
    fn = getattr(mod, attr)
    return fn


class CeleryTaskQueue:
    """Dispatch via Celery ``.delay`` / ``.apply_async``."""

    @property
    def backend_name(self) -> str:
        return "celery"

    def is_eager(self) -> bool:
        try:
            from app.core.celery_app.celery import celery_app

            return bool(celery_app.conf.task_always_eager)
        except Exception:
            from app.config import settings

            return bool(settings.CELERY_TASK_ALWAYS_EAGER)

    def enqueue(
        self,
        name: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        countdown: float = 0.0,
    ) -> EnqueueResult:
        kwargs = dict(kwargs or {})
        task = _resolve_task(name)
        if countdown and countdown > 0:
            async_result = task.apply_async(
                args=args, kwargs=kwargs, countdown=countdown
            )
        else:
            async_result = task.delay(*args, **kwargs)
        tid = getattr(async_result, "id", None) or str(uuid.uuid4())
        return EnqueueResult(
            task_id=str(tid),
            backend=self.backend_name,
            eager=self.is_eager(),
        )

    def revoke(self, task_id: str, *, terminate: bool = True) -> None:
        if not task_id:
            return
        try:
            from app.core.celery_app.celery import celery_app

            celery_app.control.revoke(task_id, terminate=terminate, signal="SIGTERM")
        except Exception as exc:
            logger.warning("Celery revoke failed for %s: %s", task_id, exc)
