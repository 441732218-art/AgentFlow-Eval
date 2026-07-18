# (c) 2026 AgentFlow-Eval
"""In-process TaskQueuePort — zero Redis/Celery broker (lite / tests)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from app.core.ports.task_queue import EnqueueResult

logger = logging.getLogger(__name__)

_TASK_MAP: dict[str, str] = {
    "run_full_evaluation": "app.core.celery_app.tasks.run_full_evaluation",
    "run_single_test_suite": "app.core.celery_app.tasks.run_single_test_suite",
    "run_judge_evaluation": "app.core.celery_app.tasks.run_judge_evaluation",
}


def _resolve_task(name: str) -> Callable[..., Any]:
    path = _TASK_MAP.get(name) or name
    mod_name, attr = path.rsplit(".", 1)
    import importlib

    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


class EagerTaskQueue:
    """Run Celery task callables synchronously in the current process.

    Works with both ``@celery_app.task`` wrapped callables (``.run`` / direct call)
    and plain functions.
    """

    @property
    def backend_name(self) -> str:
        return "eager"

    def is_eager(self) -> bool:
        return True

    def enqueue(
        self,
        name: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        countdown: float = 0.0,
    ) -> EnqueueResult:
        _ = countdown  # ignored in eager mode
        kwargs = dict(kwargs or {})
        tid = str(uuid.uuid4())
        task = _resolve_task(name)
        try:
            # Prefer Celery Task.run to avoid double-wrapping
            if hasattr(task, "run"):
                task.run(*args, **kwargs)
            else:
                task(*args, **kwargs)
        except TypeError:
            # Bound Celery tasks: first arg may be self when called wrong
            if hasattr(task, "delay"):
                # force eager path via delay when CELERY_TASK_ALWAYS_EAGER
                task.delay(*args, **kwargs)
            else:
                raise
        except Exception:
            logger.exception("Eager task %s failed", name)
            raise
        return EnqueueResult(task_id=tid, backend=self.backend_name, eager=True)

    def revoke(self, task_id: str, *, terminate: bool = True) -> None:
        # Nothing to revoke in-process after completion
        logger.debug("Eager revoke no-op for %s (terminate=%s)", task_id, terminate)
