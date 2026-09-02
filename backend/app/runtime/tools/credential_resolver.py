# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Credential resolution for remote tool HTTP transport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CredentialNotFoundError(Exception):
    """Raised when ``credential_ref`` cannot be resolved to credentials."""

    def __init__(self, credential_ref: str) -> None:
        self.credential_ref = credential_ref
        super().__init__(f"Credential not found: {credential_ref}")


class CredentialResolutionError(Exception):
    """Raised when credential resolution fails for reasons other than not found."""

    def __init__(self, credential_ref: str, message: str) -> None:
        self.credential_ref = credential_ref
        super().__init__(message)


class CredentialResolver(ABC):
    """Resolve a credential reference to credential material at request time only."""

    @abstractmethod
    def resolve(self, credential_ref: str) -> dict[str, Any]:
        """Return credential fields for ``credential_ref`` (never persist the result)."""


class InMemoryCredentialResolver(CredentialResolver):
    """Test-only resolver backed by an in-memory ref -> credentials mapping."""

    def __init__(self, credentials: dict[str, dict[str, Any] | str] | None = None) -> None:
        self._credentials = dict(credentials or {})

    def resolve(self, credential_ref: str) -> dict[str, Any]:
        ref = (credential_ref or "").strip()
        if not ref:
            raise CredentialResolutionError(ref or credential_ref, "credential_ref must be non-empty")
        if ref not in self._credentials:
            raise CredentialNotFoundError(ref)
        value = self._credentials[ref]
        if isinstance(value, str):
            return {"token": value}
        return dict(value)
