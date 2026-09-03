# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool permission binding models."""

from __future__ import annotations

from dataclasses import dataclass

from app.runtime.permissions.models import PermissionRequirement
from app.runtime.tool_registry.models import ToolCapability


@dataclass(frozen=True)
class ToolPermissionBinding:
    """Bind a tool capability to required runtime permissions."""

    tool_name: str
    permissions: tuple[PermissionRequirement, ...] = ()


def binding_from_capability(capability: ToolCapability) -> ToolPermissionBinding:
    """Build a permission binding from a tool capability scope."""
    return ToolPermissionBinding(
        tool_name=capability.tool_name,
        permissions=tuple(
            PermissionRequirement(
                permission=permission,
                description=f"Required permission for {capability.tool_name}",
            )
            for permission in capability.permission_scope
        ),
    )
