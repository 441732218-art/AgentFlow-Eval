# (c) 2026 AgentFlow-Eval
"""Sensitive-field redaction for structured logs."""

from __future__ import annotations

from typing import Any

# Exact keys (normalized: lower + hyphen→underscore)
_SENSITIVE_EXACT = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_key",
        "private_key",
        "authorization",
        "openai_api_key",
        "x_api_key",
        "bearer",
        "credential",
        "credentials",
        "refresh_token",
        "id_token",
        "session_key",
        "access_token",
        "secret_key",
    }
)

# Substring match only for high-risk stems (avoid matching total_tokens / prompt_tokens)
_SENSITIVE_SUBSTR = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "authorization",
        "api_key",
        "apikey",
        "private_key",
        "access_token",
        "refresh_token",
        "openai_api_key",
    }
)

_REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    k = key.lower().replace("-", "_")
    if k in _SENSITIVE_EXACT:
        return True
    # suffix patterns: *_password, *_secret, *_api_key
    for suffix in (
        "_password",
        "_secret",
        "_api_key",
        "_access_token",
        "_refresh_token",
        "_private_key",
    ):
        if k.endswith(suffix):
            return True
    for sk in _SENSITIVE_SUBSTR:
        if sk in k and sk != "token":
            return True
    return False


def redact_value(value: Any, *, max_str: int = 2000) -> Any:
    """Redact / truncate a single value for logging."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) > max_str:
            return value[:max_str] + f"…(+{len(value) - max_str} chars)"
        return value
    if isinstance(value, dict):
        return redact_mapping(value, max_str=max_str)
    if isinstance(value, (list, tuple)):
        return [redact_value(v, max_str=max_str) for v in value[:50]]
    # Fallback: stringify unknowns safely
    try:
        s = str(value)
    except Exception:
        return "<unrepr>"
    if len(s) > max_str:
        return s[:max_str] + "…"
    return s


def redact_mapping(
    data: dict[str, Any] | None,
    *,
    max_str: int = 2000,
) -> dict[str, Any]:
    """Return a copy of *data* with sensitive keys masked."""
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        sk = str(key)
        if _is_sensitive_key(sk):
            out[sk] = _REDACTED
        else:
            out[sk] = redact_value(value, max_str=max_str)
    return out
