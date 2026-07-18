# (c) 2026 AgentFlow-Eval
"""Tests for check-prod CLI."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.cli.check_prod import main


def _good_prod() -> SimpleNamespace:
    return SimpleNamespace(
        ENV="prod",
        is_prod=True,
        DEBUG=False,
        SECRET_KEY="a-very-strong-random-secret-key-32b",
        AUTH_ENABLED=True,
        API_KEYS="secret:ops",
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        LOG_FORMAT="json",
        CORS_ORIGINS=["https://app.example.com"],
        APP_NAME="AgentFlow-Eval",
    )


def _bad_prod() -> SimpleNamespace:
    return SimpleNamespace(
        ENV="prod",
        is_prod=True,
        DEBUG=True,
        SECRET_KEY="change-me-in-production",
        AUTH_ENABLED=False,
        API_KEYS="",
        DATABASE_URL="sqlite:///x.db",
        LOG_FORMAT="text",
        CORS_ORIGINS=["*"],
        APP_NAME="AgentFlow-Eval",
    )


def test_check_prod_ok(capsys) -> None:
    with patch("app.config.settings", _good_prod()):
        code = main(["--force-prod"])
    assert code == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_check_prod_fails_on_errors(capsys) -> None:
    with patch("app.config.settings", _bad_prod()):
        code = main(["--force-prod"])
    assert code == 1
    out = capsys.readouterr().out
    assert "ERROR" in out


def test_check_prod_strict_warnings(capsys) -> None:
    s = _good_prod()
    s.AUTH_ENABLED = False
    s.API_KEYS = ""
    with patch("app.config.settings", s):
        code = main(["--force-prod", "--strict"])
    assert code == 1
    out = capsys.readouterr().out
    assert "WARNING" in out or "strict" in out.lower()


def test_check_prod_help() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
