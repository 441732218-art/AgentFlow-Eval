# (c) 2026 AgentFlow-Eval
"""Plugin semver helpers and core compatibility checks."""

from __future__ import annotations

import re
from typing import Any

_CORE_VERSION = "0.1.0"
_SEMVER = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


def parse_semver(version: str) -> tuple[int, int, int]:
    m = _SEMVER.match((version or "").strip())
    if not m:
        return (0, 0, 0)
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def cmp_semver(a: str, b: str) -> int:
    ta, tb = parse_semver(a), parse_semver(b)
    return (ta > tb) - (ta < tb)


def satisfies(version: str, requirement: str) -> bool:
    """Minimal range: ``>=x.y.z``, ``==x.y.z``, ``*`` / empty = any."""
    req = (requirement or "").strip()
    if not req or req == "*":
        return True
    if req.startswith(">="):
        return cmp_semver(version, req[2:].strip()) >= 0
    if req.startswith("=="):
        return cmp_semver(version, req[2:].strip()) == 0
    if req.startswith(">"):
        return cmp_semver(version, req[1:].strip()) > 0
    return cmp_semver(version, req) >= 0


def check_core_requirement(requires_core: str | None) -> tuple[bool, str]:
    """Return (ok, message) for plugin requires_core field."""
    if not requires_core:
        return True, "ok"
    ok = satisfies(_CORE_VERSION, requires_core)
    if ok:
        return True, f"core {_CORE_VERSION} satisfies {requires_core}"
    return False, f"core {_CORE_VERSION} does not satisfy requires_core={requires_core}"


def plugin_version_info(meta: dict[str, Any] | None) -> dict[str, Any]:
    meta = meta or {}
    ver = str(meta.get("version") or "0.1.0")
    requires = meta.get("requires_core") or meta.get("extra", {}).get("requires_core")
    ok, msg = check_core_requirement(str(requires) if requires else None)
    return {
        "version": ver,
        "requires_core": requires,
        "compatible": ok,
        "message": msg,
        "core_version": _CORE_VERSION,
    }
