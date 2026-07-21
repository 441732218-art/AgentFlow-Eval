# (c) 2026 AgentFlow-Eval
"""Tests for production settings validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.settings_guard import (
    ProductionConfigError,
    enforce_production_settings,
    validate_settings,
)


def _settings(**overrides: object) -> SimpleNamespace:
    base = {
        "ENV": "prod",
        "is_prod": True,
        "DEBUG": False,
        "SECRET_KEY": "a-very-strong-random-secret-key-32b",
        "AUTH_ENABLED": True,
        "API_KEYS": "secret:ops",
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
        "LOG_FORMAT": "json",
        "CORS_ORIGINS": ["https://app.example.com"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestValidateSettings:
    def test_prod_valid(self) -> None:
        result = validate_settings(_settings(), strict=True)
        assert result.ok
        assert result.errors == []

    def test_prod_default_secret_rejected(self) -> None:
        result = validate_settings(
            _settings(SECRET_KEY="change-me-in-production"),
            strict=True,
        )
        assert not result.ok
        assert any("SECRET_KEY" in e for e in result.errors)

    def test_prod_debug_true_rejected(self) -> None:
        result = validate_settings(_settings(DEBUG=True), strict=True)
        assert not result.ok
        assert any("DEBUG" in e for e in result.errors)

    def test_prod_auth_without_keys_rejected(self) -> None:
        result = validate_settings(
            _settings(AUTH_ENABLED=True, API_KEYS=""),
            strict=True,
        )
        assert not result.ok
        assert any("API_KEYS" in e for e in result.errors)

    def test_prod_auth_disabled_warns(self) -> None:
        result = validate_settings(
            _settings(AUTH_ENABLED=False, API_KEYS=""),
            strict=True,
        )
        assert result.ok  # warning only
        assert any("AUTH_ENABLED" in w for w in result.warnings)

    def test_prod_sqlite_warns(self) -> None:
        result = validate_settings(
            _settings(DATABASE_URL="sqlite+aiosqlite:///./x.db"),
            strict=True,
        )
        assert result.ok
        assert any("SQLite" in w for w in result.warnings)

    def test_dev_skips_strict_checks(self) -> None:
        s = _settings(
            ENV="dev",
            is_prod=False,
            DEBUG=True,
            SECRET_KEY="change-me-in-production",
            AUTH_ENABLED=False,
        )
        result = validate_settings(s, strict=False)
        assert result.ok
        assert result.errors == []

    def test_dev_auth_enabled_empty_keys_errors(self) -> None:
        s = _settings(ENV="dev", is_prod=False, AUTH_ENABLED=True, API_KEYS="")
        result = validate_settings(s, strict=False)
        assert not result.ok


class TestEnforceProductionSettings:
    def test_enforce_raises_on_bad_prod(self) -> None:
        with pytest.raises(ProductionConfigError) as exc:
            enforce_production_settings(_settings(SECRET_KEY="change-me-in-production"))
        assert exc.value.errors

    def test_enforce_noop_on_dev(self) -> None:
        s = _settings(
            ENV="dev",
            is_prod=False,
            SECRET_KEY="change-me-in-production",
            DEBUG=True,
            AUTH_ENABLED=False,
            API_KEYS="",
        )
        result = enforce_production_settings(s)
        assert result.ok

    def test_enforce_ok_on_good_prod(self) -> None:
        result = enforce_production_settings(_settings())
        assert result.ok
