# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool provider authentication boundary — credential references only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_AUTH_TYPES = frozenset({"none", "api_key_ref", "oauth_ref", "bearer_ref"})
FORBIDDEN_CREDENTIAL_FIELDS = frozenset(
    {"api_key", "secret", "token", "password", "authorization"}
)


@dataclass(frozen=True)
class ToolProviderAuth:
    """Authentication reference for a remote provider (no secret material)."""

    auth_type: str = "none"
    credential_ref: str | None = None

    def __post_init__(self) -> None:
        auth_type = (self.auth_type or "").strip()
        if auth_type not in ALLOWED_AUTH_TYPES:
            allowed = ", ".join(sorted(ALLOWED_AUTH_TYPES))
            raise ValueError(f"ToolProviderAuth.auth_type must be one of: {allowed}")
        object.__setattr__(self, "auth_type", auth_type)
        if self.credential_ref is not None:
            ref = self.credential_ref.strip()
            object.__setattr__(self, "credential_ref", ref or None)

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any] | None) -> ToolProviderAuth:
        """Build auth config from ``ToolDefinition.metadata`` without secret fields."""
        if not metadata:
            return cls()
        auth_block = metadata.get("auth")
        if auth_block is None:
            return cls()
        if not isinstance(auth_block, dict):
            raise ValueError("ToolDefinition.metadata.auth must be a dict")
        forbidden = FORBIDDEN_CREDENTIAL_FIELDS.intersection(auth_block.keys())
        if forbidden:
            joined = ", ".join(sorted(forbidden))
            raise ValueError(
                f"ToolDefinition.metadata.auth must not contain secret fields: {joined}"
            )
        return cls(
            auth_type=str(auth_block.get("auth_type", "none")),
            credential_ref=auth_block.get("credential_ref"),
        )

    def to_metadata(self) -> dict[str, str]:
        """Return a safe metadata fragment containing references only."""
        payload: dict[str, str] = {"auth_type": self.auth_type}
        if self.credential_ref:
            payload["credential_ref"] = self.credential_ref
        return payload
