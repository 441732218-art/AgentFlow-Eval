# (c) 2026 AgentFlow-Eval
"""SSRF policy unit tests for HTTP Agent."""

from __future__ import annotations

import pytest

from app.core.agent_runner.ssrf import (
    SsrfBlockedError,
    is_url_safe_for_http_agent,
    validate_http_agent_url,
)


class TestSsrfBlocks:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/run",
            "http://localhost:8000/v1",
            "https://localhost/agent",
            "http://10.0.0.5/x",
            "http://192.168.1.1/x",
            "http://172.16.0.1/x",
            "http://172.31.255.255/x",
            "http://[::1]/",
            "http://169.254.169.254/latest/meta-data",
            "file:///etc/passwd",
            "gopher://evil",
            "ftp://example.com/a",
            "http://metadata.google.internal/",
        ],
    )
    def test_blocked(self, url: str) -> None:
        with pytest.raises(SsrfBlockedError):
            validate_http_agent_url(url, allow_private=False, resolve_dns=False)

    def test_empty(self) -> None:
        with pytest.raises(SsrfBlockedError, match="required"):
            validate_http_agent_url("", resolve_dns=False)

    def test_allow_private_opt_in(self) -> None:
        out = validate_http_agent_url(
            "http://127.0.0.1:9/run",
            allow_private=True,
            resolve_dns=False,
        )
        assert "127.0.0.1" in out


class TestSsrfAllows:
    @pytest.mark.parametrize(
        "url",
        [
            "https://agent.example.com/v1/run",
            "https://api.openai.com/v1/x",
            "http://example.com/hook",
        ],
    )
    def test_public_hosts(self, url: str) -> None:
        # resolve_dns=False — pure policy without network
        assert validate_http_agent_url(url, resolve_dns=False) == url

    def test_is_url_safe_helper(self) -> None:
        ok, err = is_url_safe_for_http_agent("http://10.1.1.1/", allow_private=False)
        assert ok is False
        assert err
        validate_http_agent_url("https://example.com/a", resolve_dns=False)
