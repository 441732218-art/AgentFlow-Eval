# (c) 2026 AgentFlow-Eval
"""Plugin commerce entitlement + paid catalog gates."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.plugins.commerce import PluginCommerceMeta
from app.core.plugins.entitlement import enforce_plugin_install
from app.core.plugins.market import reset_plugin_market
from app.core.plugins.manager import reset_plugin_manager
from app.core.plugins.sandbox import PluginSandboxPolicy
from app.main import app
from app.models.base import Base
from app.utils.exceptions import AgentFlowError

TEST_DB = "sqlite+aiosqlite:///./test_plugin_ent.db"


@pytest.fixture(autouse=True)
def _reset_plugins():
    reset_plugin_manager()
    reset_plugin_market()
    yield
    reset_plugin_manager()
    reset_plugin_market()


def test_enforce_paid_denied_on_free_plan():
    commerce = PluginCommerceMeta(
        price_cents=1999,
        is_paid=True,
        entitlement_plan=["pro", "enterprise"],
    )
    sandbox = PluginSandboxPolicy(permissions=[])
    with pytest.raises(AgentFlowError) as ei:
        enforce_plugin_install(
            catalog_id="premium_length_judge",
            commerce=commerce,
            plan_code="free",
            plan_features={"plugins": ["echo_tool"]},
            sandbox=sandbox,
            requires_core=">=0.1.0",
            actor_permissions=set(),
            force_check=True,
        )
    assert ei.value.status_code == 403


def test_enforce_paid_ok_on_pro():
    commerce = PluginCommerceMeta(
        price_cents=1999,
        is_paid=True,
        entitlement_plan=["pro", "enterprise"],
    )
    sandbox = PluginSandboxPolicy(permissions=[])
    out = enforce_plugin_install(
        catalog_id="premium_length_judge",
        commerce=commerce,
        plan_code="pro",
        plan_features={"plugins": ["*"]},
        sandbox=sandbox,
        requires_core=">=0.1.0",
        actor_permissions=set(),
        force_check=True,
    )
    assert out["ok"] is True


def test_sandbox_requires_permission_when_rbac_on():
    commerce = PluginCommerceMeta(price_cents=0)
    sandbox = PluginSandboxPolicy(permissions=["system:config"])
    with patch("app.core.plugins.entitlement.rbac_enforced", return_value=True):
        with pytest.raises(AgentFlowError) as ei:
            enforce_plugin_install(
                catalog_id="echo_tool",
                commerce=commerce,
                plan_code="free",
                plan_features={"plugins": ["*"]},
                sandbox=sandbox,
                requires_core=None,
                actor_permissions={"task:read"},
                force_check=True,
            )
        assert ei.value.status_code == 403


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)
    monkeypatch.setattr("app.config.settings.BILLING_ENABLED", False)

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
        os.remove("./test_plugin_ent.db")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_market_lists_paid_plugin(api_client):
    r = await api_client.get("/api/v1/plugins/market")
    assert r.status_code == 200, r.text
    ids = {i["id"] for i in r.json()["items"]}
    assert "premium_length_judge" in ids
    paid = next(i for i in r.json()["items"] if i["id"] == "premium_length_judge")
    assert paid.get("is_paid") is True


@pytest.mark.asyncio
async def test_install_free_ok_install_paid_denied_on_free(api_client):
    # free plugin install
    ok = await api_client.post(
        "/api/v1/plugins/market/install",
        json={"catalog_id": "echo_tool", "activate": True},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["plugin"]["state"] in {"active", "loaded"}

    # paid denied for free plan
    denied = await api_client.post(
        "/api/v1/plugins/market/install",
        json={"catalog_id": "premium_length_judge", "activate": True},
    )
    assert denied.status_code == 403, denied.text


@pytest.mark.asyncio
async def test_install_paid_after_pro_subscribe(api_client):
    sub = await api_client.post(
        "/api/v1/billing/subscribe",
        json={"plan_code": "pro"},
    )
    assert sub.status_code == 200, sub.text
    inst = await api_client.post(
        "/api/v1/plugins/market/install",
        json={"catalog_id": "premium_length_judge", "activate": True},
    )
    assert inst.status_code == 200, inst.text
