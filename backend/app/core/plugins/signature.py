# (c) 2026 AgentFlow-Eval
"""Optional plugin integrity / signature checks for production hardening.

When ``PLUGIN_SIGNATURE_CHECK=true``, every loadable plugin module path must
have a matching HMAC-SHA256 digest listed in ``PLUGIN_SIGNATURES``.

Format of PLUGIN_SIGNATURES (comma-separated)::

    module.path:hexdigest,other.mod:hexdigest

Digest = HMAC-SHA256(PLUGIN_SIGNING_SECRET, utf-8 file bytes).hexdigest()
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import logging
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def signature_check_enabled() -> bool:
    return bool(getattr(settings, "PLUGIN_SIGNATURE_CHECK", False))


def parse_signature_map(raw: str | None = None) -> dict[str, str]:
    text = raw if raw is not None else getattr(settings, "PLUGIN_SIGNATURES", "") or ""
    out: dict[str, str] = {}
    for part in str(text).split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        mod, dig = part.rsplit(":", 1)
        mod, dig = mod.strip(), dig.strip().lower()
        if mod and dig:
            out[mod] = dig
    return out


def compute_file_hmac(path: Path, secret: str) -> str:
    data = path.read_bytes()
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()


def resolve_module_file(module_entry: str) -> Path | None:
    """Resolve ``pkg.mod:Class`` or ``pkg.mod`` to a filesystem path."""
    mod_path = module_entry.split(":", 1)[0].strip()
    if not mod_path:
        return None
    try:
        spec = importlib.util.find_spec(mod_path)
    except (ModuleNotFoundError, ValueError):
        return None
    if spec is None or not spec.origin or spec.origin == "built-in":
        return None
    p = Path(spec.origin)
    return p if p.is_file() else None


def verify_plugin_entry(module_entry: str) -> tuple[bool, str]:
    """Return (ok, reason). When check disabled → always ok."""
    if not signature_check_enabled():
        return True, "disabled"
    secret = (getattr(settings, "PLUGIN_SIGNING_SECRET", None) or "").strip()
    if not secret:
        return False, "PLUGIN_SIGNING_SECRET missing while PLUGIN_SIGNATURE_CHECK=true"
    sigs = parse_signature_map()
    mod = module_entry.split(":", 1)[0].strip()
    expected = sigs.get(mod) or sigs.get(module_entry)
    if not expected:
        return False, f"no signature registered for {mod}"
    path = resolve_module_file(module_entry)
    if path is None:
        # Allow pure package path failures only if explicit digest maps to entry
        return False, f"cannot resolve module file for {mod}"
    actual = compute_file_hmac(path, secret)
    if not hmac.compare_digest(actual, expected):
        return False, f"signature mismatch for {mod}"
    return True, "ok"


def filter_signed_modules(modules: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """Filter module entries; return (allowed, rejections)."""
    if not signature_check_enabled():
        return list(modules), []
    allowed: list[str] = []
    rejected: list[dict[str, Any]] = []
    for m in modules:
        ok, reason = verify_plugin_entry(m)
        if ok:
            allowed.append(m)
        else:
            logger.warning("Plugin signature rejected %s: %s", m, reason)
            rejected.append({"module": m, "reason": reason})
    return allowed, rejected
