# (c) 2026 AgentFlow-Eval
"""Plugin management & marketplace API (commerce + sandbox gated)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.plugins.commerce import PluginCommerceMeta
from app.core.plugins.entitlement import (
    enforce_plugin_install,
    permissions_from_request,
    resolve_actor_plan,
)
from app.core.plugins.hooks import get_hook_registry
from app.core.plugins.manager import get_plugin_manager
from app.core.plugins.market import get_plugin_market
from app.core.plugins.sandbox import PluginSandboxPolicy
from app.core.rbac import Permission, require_permission
from app.utils.exceptions import AgentFlowError

router = APIRouter()


class LoadPluginBody(BaseModel):
    entry: str | None = Field(None, description="Python entry module:Class")
    path: str | None = Field(None, description="Filesystem path to plugin package")
    plugin_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    activate: bool = True


class MarketInstallBody(BaseModel):
    catalog_id: str
    activate: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


async def _audit(
    request: Request,
    session: AsyncSession | None,
    *,
    action: str,
    resource_id: str,
    detail: dict[str, Any] | None = None,
) -> None:
    if session is None:
        return
    try:
        from app.core.audit import write_audit

        await write_audit(
            session,
            action=action,
            resource_type="plugin",
            resource_id=resource_id,
            actor=_actor(request),
            detail=detail or {},
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception:
        pass


@router.get("")
@require_permission(Permission.SYSTEM_CONFIG)
async def list_plugins(
    request: Request,
    state: str | None = Query(None),
    plugin_type: str | None = Query(None, alias="type"),
) -> dict[str, Any]:
    """List discovered / loaded plugins."""
    mgr = get_plugin_manager()
    items = mgr.list_plugins(state=state, plugin_type=plugin_type)
    return {"items": items, "total": len(items), "status": mgr.status()}


@router.get("/status")
@require_permission(Permission.TASK_READ)
async def plugin_status(request: Request) -> dict[str, Any]:
    """Capability summary (runners / judges / tools / hooks)."""
    return get_plugin_manager().status()


@router.get("/hooks")
@require_permission(Permission.SYSTEM_CONFIG)
async def list_hooks(
    request: Request,
    name: str | None = Query(None, description="Filter by hook name"),
) -> dict[str, Any]:
    hooks = get_hook_registry().list_hooks(name)
    return {"items": hooks, "total": len(hooks)}


@router.get("/market")
@require_permission(Permission.TASK_READ)
async def market_list(
    request: Request,
    tag: str | None = None,
    plugin_type: str | None = Query(None, alias="type"),
    installed_only: bool = False,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Local plugin marketplace catalog (optional)."""
    market = get_plugin_market()
    if not market.list_catalog():
        market.seed_builtin_catalog()
    items = market.list_catalog(
        tag=tag, plugin_type=plugin_type, installed_only=installed_only
    )
    plan_code, features = await resolve_actor_plan(session, _actor(request))
    # Annotate entitlement for UI
    enriched = []
    for it in items:
        try:
            meta = market.commerce_for(it["id"])
            commerce = PluginCommerceMeta.from_mapping(meta.get("commerce"))
            from app.core.plugins.commerce import check_entitlement

            ok, reason = check_entitlement(
                commerce,
                plan_code=plan_code,
                plan_features=features,
                plugin_id=it["id"],
            )
            it = {**it, "entitled": ok, "entitlement_reason": reason}
        except Exception:
            it = {**it, "entitled": True, "entitlement_reason": "unknown"}
        enriched.append(it)
    return {
        "items": enriched,
        "total": len(enriched),
        "plan_code": plan_code,
    }


@router.get("/market/{catalog_id}/meta")
@require_permission(Permission.TASK_READ)
async def market_plugin_meta(
    request: Request,
    catalog_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Commerce + sandbox + version metadata for a catalog plugin."""
    market = get_plugin_market()
    if not market.list_catalog():
        market.seed_builtin_catalog()
    try:
        meta = market.commerce_for(catalog_id)
    except KeyError as exc:
        raise AgentFlowError(str(exc), status_code=404) from exc
    plan_code, features = await resolve_actor_plan(session, _actor(request))
    commerce = PluginCommerceMeta.from_mapping(meta.get("commerce"))
    from app.core.plugins.commerce import check_entitlement

    ok, reason = check_entitlement(
        commerce, plan_code=plan_code, plan_features=features, plugin_id=catalog_id
    )
    meta["entitled"] = ok
    meta["entitlement_reason"] = reason
    meta["plan_code"] = plan_code
    return meta


@router.post("/market/install")
@require_permission(Permission.SYSTEM_CONFIG)
async def market_install(
    request: Request,
    body: MarketInstallBody,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    market = get_plugin_market()
    if not market.list_catalog():
        market.seed_builtin_catalog()
    try:
        meta = market.commerce_for(body.catalog_id)
    except KeyError as exc:
        raise AgentFlowError(str(exc), status_code=404) from exc

    plan_code, features = await resolve_actor_plan(session, _actor(request))
    commerce = PluginCommerceMeta.from_mapping(meta.get("commerce"))
    sandbox = PluginSandboxPolicy.from_mapping(meta.get("sandbox"))
    requires = None
    ver = meta.get("version") or {}
    if isinstance(ver, dict):
        requires = ver.get("requires_core") or meta.get("requires_core")
    else:
        requires = meta.get("requires_core")

    gate = enforce_plugin_install(
        catalog_id=body.catalog_id,
        commerce=commerce,
        plan_code=plan_code,
        plan_features=features,
        sandbox=sandbox,
        requires_core=str(requires) if requires else None,
        actor_permissions=permissions_from_request(request),
        force_check=True,
    )

    try:
        rec = market.install(
            body.catalog_id, activate=body.activate, config=body.config
        )
    except KeyError as exc:
        raise AgentFlowError(str(exc), status_code=404) from exc
    except Exception as exc:
        raise AgentFlowError(f"install failed: {exc}", status_code=400) from exc

    await _audit(
        request,
        session,
        action="plugin.install",
        resource_id=body.catalog_id,
        detail={"gate": gate, "activate": body.activate, "state": rec.get("state")},
    )
    await session.commit()
    return {"plugin": rec, "entitlement": gate}


@router.post("/market/uninstall")
@require_permission(Permission.SYSTEM_CONFIG)
async def market_uninstall(
    request: Request,
    body: MarketInstallBody,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    market = get_plugin_market()
    try:
        rec = market.uninstall(body.catalog_id)
    except KeyError as exc:
        raise AgentFlowError(str(exc), status_code=404) from exc
    await _audit(
        request,
        session,
        action="plugin.uninstall",
        resource_id=body.catalog_id,
        detail={"state": rec.get("state")},
    )
    await session.commit()
    return {"plugin": rec}


@router.post("/load")
@require_permission(Permission.SYSTEM_CONFIG)
async def load_plugin(
    request: Request,
    body: LoadPluginBody,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dynamically load a plugin from entry or path."""
    if not body.entry and not body.path:
        raise AgentFlowError("entry or path is required", status_code=400)
    mgr = get_plugin_manager()
    try:
        rec = mgr.load(
            plugin_id=body.plugin_id,
            entry=body.entry,
            path=body.path,
            config=body.config,
            activate=body.activate,
        )
    except Exception as exc:
        raise AgentFlowError(f"load failed: {exc}", status_code=400) from exc
    if rec.state.value == "error":
        raise AgentFlowError(rec.error or "plugin load error", status_code=400)
    await _audit(
        request,
        session,
        action="plugin.load",
        resource_id=rec.plugin_id,
        detail={"entry": body.entry, "path": body.path},
    )
    await session.commit()
    return {"plugin": rec.to_dict()}


@router.get("/{plugin_id}")
@require_permission(Permission.SYSTEM_CONFIG)
async def get_plugin(request: Request, plugin_id: str) -> dict[str, Any]:
    rec = get_plugin_manager().get(plugin_id)
    if rec is None:
        raise AgentFlowError(f"plugin not found: {plugin_id}", status_code=404)
    return {"plugin": rec.to_dict()}


@router.post("/{plugin_id}/activate")
@require_permission(Permission.SYSTEM_CONFIG)
async def activate_plugin(
    request: Request,
    plugin_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    mgr = get_plugin_manager()
    if mgr.get(plugin_id) is None:
        raise AgentFlowError(f"plugin not found: {plugin_id}", status_code=404)

    # Re-check sandbox when catalog meta known
    market = get_plugin_market()
    if not market.list_catalog():
        market.seed_builtin_catalog()
    try:
        meta = market.commerce_for(plugin_id)
        plan_code, features = await resolve_actor_plan(session, _actor(request))
        commerce = PluginCommerceMeta.from_mapping(meta.get("commerce"))
        sandbox = PluginSandboxPolicy.from_mapping(meta.get("sandbox"))
        ver = meta.get("version") or {}
        requires = (
            ver.get("requires_core")
            if isinstance(ver, dict)
            else meta.get("requires_core")
        )
        enforce_plugin_install(
            catalog_id=plugin_id,
            commerce=commerce,
            plan_code=plan_code,
            plan_features=features,
            sandbox=sandbox,
            requires_core=str(requires) if requires else None,
            actor_permissions=permissions_from_request(request),
            force_check=True,
        )
    except AgentFlowError:
        raise
    except KeyError:
        # Not a catalog plugin — allow activate for custom loads
        pass
    except Exception:
        pass

    try:
        rec = mgr.activate(plugin_id)
    except Exception as exc:
        raise AgentFlowError(str(exc), status_code=400) from exc
    await _audit(
        request,
        session,
        action="plugin.activate",
        resource_id=plugin_id,
        detail={"state": rec.state.value},
    )
    await session.commit()
    return {"plugin": rec.to_dict()}


@router.post("/{plugin_id}/deactivate")
@require_permission(Permission.SYSTEM_CONFIG)
async def deactivate_plugin(
    request: Request,
    plugin_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    mgr = get_plugin_manager()
    if mgr.get(plugin_id) is None:
        raise AgentFlowError(f"plugin not found: {plugin_id}", status_code=404)
    rec = mgr.deactivate(plugin_id)
    await _audit(
        request,
        session,
        action="plugin.deactivate",
        resource_id=plugin_id,
        detail={"state": rec.state.value},
    )
    await session.commit()
    return {"plugin": rec.to_dict()}


@router.post("/{plugin_id}/reload")
@require_permission(Permission.SYSTEM_CONFIG)
async def reload_plugin(
    request: Request,
    plugin_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    mgr = get_plugin_manager()
    if mgr.get(plugin_id) is None:
        raise AgentFlowError(f"plugin not found: {plugin_id}", status_code=404)
    try:
        rec = mgr.reload(plugin_id)
    except Exception as exc:
        raise AgentFlowError(str(exc), status_code=400) from exc
    await _audit(
        request,
        session,
        action="plugin.reload",
        resource_id=plugin_id,
        detail={"state": rec.state.value},
    )
    await session.commit()
    return {"plugin": rec.to_dict()}


@router.delete("/{plugin_id}")
@require_permission(Permission.SYSTEM_CONFIG)
async def unload_plugin(
    request: Request,
    plugin_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    mgr = get_plugin_manager()
    if mgr.get(plugin_id) is None:
        raise AgentFlowError(f"plugin not found: {plugin_id}", status_code=404)
    rec = mgr.unload(plugin_id)
    await _audit(
        request,
        session,
        action="plugin.unload",
        resource_id=plugin_id,
        detail={"state": rec.state.value},
    )
    await session.commit()
    return {"plugin": rec.to_dict()}
