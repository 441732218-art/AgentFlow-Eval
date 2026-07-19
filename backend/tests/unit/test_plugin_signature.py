# (c) 2026 AgentFlow-Eval
"""Plugin signature / strict mode unit tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.core.plugins.signature import (
    compute_file_hmac,
    filter_signed_modules,
    parse_signature_map,
    signature_check_enabled,
    verify_plugin_entry,
)


def test_parse_signature_map():
    m = parse_signature_map("a.b:deadbeef,c.d:cafebabe")
    assert m["a.b"] == "deadbeef"
    assert m["c.d"] == "cafebabe"


def test_signature_disabled_allows_all():
    with patch("app.core.plugins.signature.settings") as s:
        s.PLUGIN_SIGNATURE_CHECK = False
        assert signature_check_enabled() is False
        ok, reason = verify_plugin_entry("app.plugins.examples.echo_tool:Plugin")
        assert ok and reason == "disabled"


def test_hmac_file(tmp_path: Path):
    f = tmp_path / "p.py"
    f.write_text("print('ok')\n", encoding="utf-8")
    dig = compute_file_hmac(f, "secret")
    assert len(dig) == 64
    assert dig == compute_file_hmac(f, "secret")
    assert dig != compute_file_hmac(f, "other")


def test_filter_when_enabled_rejects_unsigned():
    with patch("app.core.plugins.signature.settings") as s:
        s.PLUGIN_SIGNATURE_CHECK = True
        s.PLUGIN_SIGNING_SECRET = "s"
        s.PLUGIN_SIGNATURES = ""
        allowed, rejected = filter_signed_modules(
            ["app.plugins.examples.echo_tool:Plugin"]
        )
        assert allowed == []
        assert len(rejected) == 1
