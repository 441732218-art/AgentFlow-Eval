# (c) 2026 AgentFlow-Eval
"""E2E-ish: BILLING_ENABLED → task quota exhausted → execute returns 402."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.ports.task_queue import EnqueueResult
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_billing_402.db"


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", True)
    # service module may cache flag via function billing_enabled reading settings
    monkeypatch.setattr(
        "app.core.billing.service.billing_enabled",
        lambda: True,
    )

    engine = create_async_engine(TEST_DB, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_billing_402.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_execute_blocked_when_task_quota_exhausted(api_client):
    # Seed plans + fill quota for anonymous (default actor when auth off)
    from app.core.billing.service import get_billing_service
    from app.core.dependencies import async_session_factory  # may not match test db

    # Use API to get quota then force limit via service on same overridden DB
    # Direct: call subscribe + max out through billing API session via app dependency
    r = await api_client.get("/api/v1/billing/quota")
    assert r.status_code == 200

    # Exhaust via repeated execute after setting task_used = task_limit
    # Inject by calling internal service with the client session is hard;
    # instead patch ensure_task_quota to raise, then also test real path via service unit.

    from app.core.billing.service import QuotaExceededError

    async def _raise_quota(*_a, **_k):
        raise QuotaExceededError(
            "Task quota exceeded for this billing period",
            detail={"task_used": 50, "task_limit": 50},
        )

    created = await api_client.post(
        "/api/v1/tasks",
        json={"name": "quota-block", "description": "", "agent_config": {}},
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    mock_q = MagicMock()
    mock_q.enqueue.return_value = EnqueueResult(
        task_id="never", backend="eager", eager=True
    )
    with patch(
        "app.core.billing.service.BillingService.ensure_task_quota",
        new=_raise_quota,
    ):
        with patch("app.core.profiles.get_task_queue", return_value=mock_q):
            ex = await api_client.post(f"/api/v1/tasks/{tid}/execute")

    assert ex.status_code == 402, ex.text
    body = ex.json()
    # Unified error envelope
    msg = body.get("error", {}).get("message") or body.get("detail") or ""
    assert "quota" in str(msg).lower() or "Quota" in str(msg)
    mock_q.enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_execute_ok_when_quota_available(api_client):
    created = await api_client.post(
        "/api/v1/tasks",
        json={"name": "quota-ok", "description": "", "agent_config": {}},
    )
    tid = created.json()["id"]
    mock_q = MagicMock()
    mock_q.enqueue.return_value = EnqueueResult(
        task_id="job-ok", backend="eager", eager=True
    )
    with patch("app.core.profiles.get_task_queue", return_value=mock_q):
        ex = await api_client.post(f"/api/v1/tasks/{tid}/execute")
    assert ex.status_code == 200, ex.text
    assert ex.json()["celery_task_id"] == "job-ok"
