# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Credential resolution for remote tool HTTP transport."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CredentialResolver(ABC):
    """Resolve a credential reference to a secret value at request time only."""

    @abstractmethod
    def resolve(self, credential_ref: str) -> str:
        """Return the secret value for ``credential_ref``."""


class InMemoryCredentialResolver(CredentialResolver):
    """Test-only resolver backed by an in-memory ref -> secret mapping."""

    def __init__(self, credentials: dict[str, str] | None = None) -> None:
        self._credentials = dict(credentials or {})

    def resolve(self, credential_ref: str) -> str:
        ref = (credential_ref or "").strip()
        if not ref:
            raise ValueError("credential_ref must be a non-empty string")
        if ref not in self._credentials:
            raise KeyError(f"Unknown credential_ref: {ref}")
        return self._credentials[ref]
