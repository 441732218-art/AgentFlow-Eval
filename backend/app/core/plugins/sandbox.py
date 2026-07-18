# (c) 2026 AgentFlow-Eval
"""Plugin sandbox declarations — permission & resource constraints."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PluginSandboxPolicy:
    """Declarative isolation policy (enforced at activate time)."""

    allow_network: bool = False
    max_cpu_ms: int = 30_000
    max_memory_mb: int = 512
    # Required host permissions (RBAC strings) to activate
    permissions: list[str] = field(default_factory=list)
    # Filesystem roots allowed (empty = none beyond in-memory)
    allowed_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "PluginSandboxPolicy":
        data = data or {}
        return cls(
            allow_network=bool(data.get("allow_network", False)),
            max_cpu_ms=int(data.get("max_cpu_ms") or 30_000),
            max_memory_mb=int(data.get("max_memory_mb") or 512),
            permissions=list(data.get("permissions") or []),
            allowed_paths=list(data.get("allowed_paths") or []),
        )


def validate_activate(
    policy: PluginSandboxPolicy,
    *,
    actor_permissions: set[str] | None = None,
    rbac_enforced: bool = False,
) -> tuple[bool, str]:
    """Check whether caller may activate plugin under policy."""
    if not rbac_enforced:
        return True, "rbac off"
    needed = set(policy.permissions or [])
    if not needed:
        return True, "no extra permissions"
    have = actor_permissions or set()
    missing = needed - have
    if missing:
        return False, f"missing permissions: {sorted(missing)}"
    return True, "ok"
