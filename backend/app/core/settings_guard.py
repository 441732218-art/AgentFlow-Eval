# (c) 2026 AgentFlow-Eval
"""Production settings validation — fail fast on insecure prod config."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

# Well-known insecure defaults that must never ship to production.
_INSECURE_SECRET_KEYS = frozenset(
    {
        "change-me-in-production",
        "secret",
        "changeme",
        "dev",
        "development",
        "test",
        "password",
        "",
    }
)

_WEAK_SECRET_RE = re.compile(r"^(.)\1{7,}$")  # e.g. aaaaaaaa


class ProductionConfigError(RuntimeError):
    """Raised when production configuration fails hard security checks."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        message = "Production configuration invalid:\n  - " + "\n  - ".join(self.errors)
        super().__init__(message)


@dataclass
class SettingsValidationResult:
    """Outcome of validating application settings for a target environment."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no hard errors were found."""
        return not self.errors


def validate_settings(
    settings: Settings,
    *,
    strict: bool | None = None,
) -> SettingsValidationResult:
    """Validate settings for the current (or forced) environment.

    Args:
        settings: Application settings instance.
        strict: When True, apply production rules. When None, use ``settings.is_prod``.

    Returns:
        SettingsValidationResult with ``errors`` (must fix) and ``warnings`` (should fix).
    """
    result = SettingsValidationResult()
    use_strict = settings.is_prod if strict is None else strict

    if not use_strict:
        # Light checks for all environments
        if settings.AUTH_ENABLED and not str(settings.API_KEYS or "").strip():
            result.errors.append(
                "AUTH_ENABLED=true but API_KEYS is empty — authentication would lock out all clients"
            )
        return result

    # ---- Hard errors (block startup) ----
    secret = (settings.SECRET_KEY or "").strip()
    if secret.lower() in _INSECURE_SECRET_KEYS or len(secret) < 16:
        result.errors.append(
            "SECRET_KEY must be a strong random string (≥16 chars); "
            "do not use the default 'change-me-in-production'"
        )
    elif _WEAK_SECRET_RE.match(secret):
        result.errors.append("SECRET_KEY looks weak (repeated single character)")

    if settings.DEBUG:
        result.errors.append("DEBUG must be false when ENV=prod (leaks stacktraces)")

    if settings.AUTH_ENABLED and not str(settings.API_KEYS or "").strip():
        result.errors.append("AUTH_ENABLED=true requires a non-empty API_KEYS list")

    # ---- Warnings (log only) ----
    if not settings.AUTH_ENABLED:
        result.warnings.append(
            "AUTH_ENABLED=false in production — API is publicly reachable; "
            "enable AUTH_ENABLED and set API_KEYS for enterprise deployments"
        )

    db_url = (settings.DATABASE_URL or "").lower()
    if db_url.startswith("sqlite"):
        result.warnings.append(
            "DATABASE_URL uses SQLite in production — prefer PostgreSQL for concurrency and durability"
        )

    if settings.LOG_FORMAT != "json":
        result.warnings.append(
            "LOG_FORMAT is not 'json' — structured JSON logs are recommended for production aggregators"
        )

    cors = settings.CORS_ORIGINS or []
    if "*" in cors:
        result.warnings.append(
            "CORS_ORIGINS contains '*' — restrict origins to known frontends in production"
        )

    if not cors:
        result.warnings.append("CORS_ORIGINS is empty — browser clients may be blocked")

    return result


def enforce_production_settings(settings: Settings) -> SettingsValidationResult:
    """Run validation and raise ProductionConfigError on hard failures.

    Always logs warnings. Only enforces errors when ``settings.is_prod``.

    Args:
        settings: Application settings instance.

    Returns:
        The validation result (empty errors when not in prod).

    Raises:
        ProductionConfigError: When ENV=prod and hard errors exist.
    """
    result = validate_settings(settings, strict=settings.is_prod)

    for warning in result.warnings:
        logger.warning("Config warning: %s", warning)

    if settings.is_prod and result.errors:
        for err in result.errors:
            logger.error("Config error: %s", err)
        raise ProductionConfigError(result.errors)

    if result.ok and settings.is_prod:
        logger.info("Production settings validation passed")

    return result
