# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Environment-variable credential resolver."""

from __future__ import annotations

import os
from typing import Any

from app.runtime.tools.credential_resolver import (
    CredentialNotFoundError,
    CredentialResolutionError,
    CredentialResolver,
)

ENV_SCHEME = "env://"


class EnvCredentialResolver(CredentialResolver):
    """Resolve ``env://KEY_NAME`` references from process environment variables."""

    def resolve(self, credential_ref: str) -> dict[str, Any]:
        ref = (credential_ref or "").strip()
        if not ref.startswith(ENV_SCHEME):
            raise CredentialResolutionError(
                ref,
                f"EnvCredentialResolver supports {ENV_SCHEME} references only",
            )
        env_key = ref[len(ENV_SCHEME) :].strip()
        if not env_key:
            raise CredentialResolutionError(ref, "Environment variable name must be non-empty")

        value = os.environ.get(env_key)
        if value is None or value == "":
            raise CredentialNotFoundError(ref)

        return {"api_key": value}
