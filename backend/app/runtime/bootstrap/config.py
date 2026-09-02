# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Production runtime bootstrap configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RuntimeConfig:
    """Secure defaults for assembling a production Agent Runtime instance."""

    environment: str = "production"
    enable_governance: bool = True
    enable_observation: bool = True
    enable_audit: bool = True
    credential_resolver_type: str = "env"
    application_providers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.environment not in {"production", "staging", "development", "test"}:
            raise ValueError(
                "environment must be one of: production, staging, development, test"
            )
        if self.credential_resolver_type not in {"env", "none"}:
            raise ValueError("credential_resolver_type must be 'env' or 'none'")
