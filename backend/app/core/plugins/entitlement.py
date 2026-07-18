# (c) 2026 AgentFlow-Eval
"""Plugin install entitlement — plan features + commerce + sandbox."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.plugins.commerce import PluginCommerceMeta, check_entitlement
from app.core.plugins.sandbox import PluginSandboxPolicy, validate_activate
from app.core.plugins.versioning import check_core_requirement
from app.core.rbac import Permission, get_request_role, permissions_for, rbac_enforced
from app.utils.exceptions import AgentFlowError

logger = logging.getLogger(__name__)


async def resolve_actor_plan(
    session: AsyncSession | None,
    actor: str,
) -> tuple[str, dict[str, Any]]:
    """Return (plan_code, features) for actor. Defaults to free catalog plan."""
    plan_code = "free"
    features: dict[str, Any] = {
        "plugins": ["echo_tool", "audit_hooks", "length_judge", "echo_runner"],
        "vision": False,
    }
    try:
        from app.core.billing.service import get_billing_service

        svc = get_billing_service()
        if session is not None:
            await svc.ensure_default_plans(session)
            sub = await svc.get_active_subscription(session, actor)
            if sub is not None:
                from sqlalchemy import select
                from app.models.billing import BillingPlan

                r = await session.execute(
                    select(BillingPlan).where(BillingPlan.id == sub.plan_id)
                )
                plan = r.scalar_one_or_none()
                if plan is not None:
                    plan_code = plan.code
                    features = dict(plan.features or {})
            else:
                free = await svc.get_plan_by_code(session, "free")
                if free is not None:
                    plan_code = free.code
                    features = dict(free.features or features)
    except Exception as exc:
        logger.debug("resolve_actor_plan fallback free: %s", exc)
    return plan_code, features


def enforce_plugin_install(
    *,
    catalog_id: str,
    commerce: PluginCommerceMeta,
    plan_code: str,
    plan_features: dict[str, Any],
    sandbox: PluginSandboxPolicy,
    requires_core: str | None,
    actor_permissions: set[str] | None,
    force_check: bool = False,
) -> dict[str, Any]:
    """Hard checks for install/activate. Raises AgentFlowError on deny.

    When BILLING_ENABLED is false, free plugins still pass; paid plugins are
    denied unless plan explicitly includes them or force_check is false and
    commerce is free.
    """
    # Core version
    ok, msg = check_core_requirement(requires_core)
    if not ok:
        raise AgentFlowError(f"plugin incompatible: {msg}", status_code=400)

    billing_on = bool(getattr(settings, "BILLING_ENABLED", False))
    # Always enforce paid entitlement; free plugins use plan allow-list when billing on
    if commerce.is_paid or commerce.price_cents > 0 or billing_on or force_check:
        ok_e, reason = check_entitlement(
            commerce,
            plan_code=plan_code,
            plan_features=plan_features,
            plugin_id=catalog_id,
        )
        if not ok_e:
            raise AgentFlowError(
                f"plugin entitlement denied: {reason}",
                status_code=403,
                detail={
                    "catalog_id": catalog_id,
                    "plan_code": plan_code,
                    "is_paid": commerce.is_paid or commerce.price_cents > 0,
                },
            )
        # plan features allow-list (even free plugins when billing on)
        if billing_on and plan_features:
            from app.core.billing.service import get_billing_service

            if not get_billing_service().plan_allows_plugin(plan_features, catalog_id):
                # Wildcard / free list handling already in plan_allows_plugin;
                # paid plugins entitled by plan still need allow if list is exclusive
                plugins = plan_features.get("plugins")
                if plugins not in (None, ["*"], "*") and catalog_id not in set(
                    plugins or []
                ):
                    # If entitled via commerce plan list but not in free feature list,
                    # allow paid when commerce entitlement_plan matches
                    if not (commerce.is_paid or commerce.price_cents > 0):
                        raise AgentFlowError(
                            f"plan {plan_code} does not include plugin {catalog_id}",
                            status_code=403,
                        )

    # Sandbox permission gate
    ok_s, smsg = validate_activate(
        sandbox,
        actor_permissions=actor_permissions,
        rbac_enforced=rbac_enforced(),
    )
    if not ok_s:
        raise AgentFlowError(
            f"plugin sandbox denied: {smsg}",
            status_code=403,
            detail={"sandbox": sandbox.to_dict()},
        )

    return {
        "ok": True,
        "plan_code": plan_code,
        "core": msg,
        "sandbox": smsg,
    }


def permissions_from_request(request: Any) -> set[str]:
    role = get_request_role(request)
    return {p.value for p in permissions_for(role)}
