# (c) 2026 AgentFlow-Eval
"""Built-in tool registry listing for UI / docs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.agent_runner.tool_sandbox import BUILTIN_TOOLS, run_tool_sandboxed
from app.core.rbac import Permission, require_permission

router = APIRouter()


class ToolProbeRequest(BaseModel):
    name: str = Field(..., description="Tool name")
    args: dict[str, Any] = Field(default_factory=dict)


@router.get("")
@require_permission(Permission.TASK_READ)
async def list_tools(request: Request) -> dict[str, Any]:
    """List sandboxed built-in and plugin tools available to agents."""
    items = []
    for name, meta in sorted(BUILTIN_TOOLS.items()):
        items.append(
            {
                "name": name,
                "description": meta["description"],
                "parameters": meta["parameters"],
                "required": meta.get("required") or [],
                "sandbox": True,
                "network": False,
                "source": "builtin",
            }
        )
    try:
        from app.core.plugins.registry import get_capability_registry

        for t in get_capability_registry().list_tools():
            items.append(
                {
                    "name": t["name"],
                    "description": t.get("description") or "",
                    "parameters": t.get("parameters") or {},
                    "required": t.get("required") or [],
                    "sandbox": True,
                    "network": bool(t.get("network")),
                    "source": "plugin",
                    "plugin_id": t.get("plugin_id"),
                }
            )
    except Exception:
        pass
    return {"items": items, "total": len(items)}


@router.post("/probe")
@require_permission(Permission.SYSTEM_CONFIG)
async def probe_tool(request: Request, body: ToolProbeRequest) -> dict[str, Any]:
    """Execute a built-in tool once (dev/debug). Requires system:config."""
    output = run_tool_sandboxed(body.name, body.args)
    return {"name": body.name, "args": body.args, "output": output}
