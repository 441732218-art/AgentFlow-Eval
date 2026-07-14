# (c) 2026 AgentFlow-Eval
"""Built-in tool registry listing for UI / docs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.agent_runner.tool_sandbox import BUILTIN_TOOLS, run_tool_sandboxed

router = APIRouter()


class ToolProbeRequest(BaseModel):
    name: str = Field(..., description="Tool name")
    args: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_tools() -> dict[str, Any]:
    """List sandboxed built-in tools available to agents."""
    items = []
    for name, meta in sorted(BUILTIN_TOOLS.items()):
        items.append({
            "name": name,
            "description": meta["description"],
            "parameters": meta["parameters"],
            "required": meta.get("required") or [],
            "sandbox": True,
            "network": False,
        })
    return {"items": items, "total": len(items)}


@router.post("/probe")
async def probe_tool(body: ToolProbeRequest) -> dict[str, Any]:
    """Execute a built-in tool once (dev/debug). No custom code allowed."""
    output = run_tool_sandboxed(body.name, body.args)
    return {"name": body.name, "args": body.args, "output": output}
