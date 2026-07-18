# (c) 2026 AgentFlow-Eval
"""Background thread TaskQueuePort — fire-and-forget without Redis."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Callable

from app.core.ports.task_queue import EnqueueResult

logger = logging.getLogger(__name__)

_TASK_MAP: dict[str, str] = {
    "run_full_evaluation": "app.core.celery_app.tasks.run_full_evaluation",
    "run_single_test_suite": "app.core.celery_app.tasks.run_single_test_suite",
    "run_judge_evaluation": "app.core.celery_app.tasks.run_judge_evaluation",
}

_jobs: dict[str, threading.Thread] = {}
_lock = threading.Lock()


def _resolve_task(name: str) -> Callable[..., Any]:
    path = _TASK_MAP.get(name) or name
    mod_name, attr = path.rsplit(".", 1)
    import importlib

    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


class MemoryTaskQueue:
    """Spawn a daemon thread per job (demo / single-node)."""

    @property
    def backend_name(self) -> str:
        return "memory"

    def is_eager(self) -> bool:
        return False

    def enqueue(
        self,
        name: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        countdown: float = 0.0,
    ) -> EnqueueResult:
        kwargs = dict(kwargs or {})
        tid = str(uuid.uuid4())
        task = _resolve_task(name)

        def _run() -> None:
            if countdown and countdown > 0:
                import time

                time.sleep(float(countdown))
            try:
                if hasattr(task, "run"):
                    task.run(*args, **kwargs)
                else:
                    task(*args, **kwargs)
            except Exception:
                logger.exception("Memory task %s (%s) failed", name, tid)

        t = threading.Thread(target=_run, name=f"mem-queue-{name}", daemon=True)
        with _lock:
            _jobs[tid] = t
        t.start()
        return EnqueueResult(task_id=tid, backend=self.backend_name, eager=False)

    def revoke(self, task_id: str, *, terminate: bool = True) -> None:
        # Threads cannot be force-killed safely; best-effort join skip
        logger.debug("Memory revoke no-op for %s", task_id)
