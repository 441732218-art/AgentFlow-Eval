# (c) 2026 AgentFlow-Eval
"""SQLAlchemy metering — persists usage_records when BILLING_ENABLED."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SqlAlchemyMeter:
    """Best-effort sync-looking API; schedules async write when loop available.

    For Celery workers we open a short async session via asyncio.run-free path:
    records go through a thread-local fire-and-forget when possible.
    """

    @property
    def backend_name(self) -> str:
        return "sqlalchemy"

    def record(
        self,
        *,
        actor: str,
        metric: str,
        quantity: float = 1.0,
        ref_type: str | None = None,
        ref_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        try:
            from app.config import settings

            if not getattr(settings, "BILLING_ENABLED", False):
                return
        except Exception:
            return

        trace_id = None
        try:
            from app.core.observability.tracing import get_trace_id

            trace_id = get_trace_id() or None
        except Exception:
            pass

        try:
            import asyncio

            async def _write() -> None:
                from app.core.billing.service import get_billing_service
                from app.core.dependencies import async_session_factory

                svc = get_billing_service()
                async with async_session_factory() as session:
                    try:
                        await svc.record_usage(
                            session,
                            actor=actor or "anonymous",
                            metric=metric,
                            quantity=quantity,
                            ref_type=ref_type,
                            ref_id=ref_id,
                            trace_id=trace_id,
                            extra=extra,
                        )
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_write())
            except RuntimeError:
                # No running loop (Celery worker thread) — use asyncio.run
                asyncio.run(_write())
        except Exception as exc:
            logger.debug("SqlAlchemyMeter.record skipped: %s", exc)
