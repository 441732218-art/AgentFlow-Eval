# (c) 2026 AgentFlow-Eval
"""SSRF guards for HttpAgentRunner and HTTP probe API.

Blocks private / loopback / link-local / cloud-metadata targets and non-HTTP
schemes unless explicitly allowed via settings (tests / controlled labs).
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from urllib.parse import urlparse

# Hostnames that must never be called (case-insensitive)
_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata",
        "metadata.google.internal",
    }
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})

# AWS / Azure / GCP style metadata endpoints often resolve to link-local
_METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.goog",
    }
)


class SsrfBlockedError(ValueError):
    """Raised when a URL is rejected by SSRF policy."""

    def __init__(self, message: str, *, url: str = "") -> None:
        self.url = url
        super().__init__(message)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if IP is not safe for outbound agent calls."""
    if ip.is_private:
        return True
    if ip.is_loopback:
        return True
    if ip.is_link_local:
        return True
    if ip.is_multicast:
        return True
    if ip.is_reserved:
        return True
    if ip.is_unspecified:
        return True
    # IPv6 unique local / site local
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _is_blocked_ip(ip.ipv4_mapped)
    return False


def _hostname_looks_local(host: str) -> bool:
    h = host.lower().rstrip(".")
    if h in _BLOCKED_HOSTNAMES or h in _METADATA_HOSTS:
        return True
    if h.endswith(".localhost") or h.endswith(".local"):
        return True
    # Decimal / hex IP literal forms of loopback sometimes appear
    if h in {"0", "0.0.0.0", "::", "[::]"}:
        return True
    return False


def _parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Try parse host as IP (handles [ipv6] brackets)."""
    h = host.strip()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    try:
        return ipaddress.ip_address(h)
    except ValueError:
        return None


def validate_http_agent_url(
    url: str,
    *,
    allow_private: bool = False,
    resolve_dns: bool = True,
) -> str:
    """Validate URL for HTTP agent / probe use.

    Args:
        url: Absolute URL string.
        allow_private: When True, skip private/loopback IP checks (dev/tests).
        resolve_dns: When True, resolve hostname and check all A/AAAA records.

    Returns:
        Normalized URL string (strip).

    Raises:
        SsrfBlockedError: When the URL violates policy.
    """
    raw = (url or "").strip()
    if not raw:
        raise SsrfBlockedError("endpoint_url is required", url=url)

    # Reject obvious non-http schemes early (file, gopher, etc.)
    lowered = raw.lower()
    if re.match(r"^[a-z][a-z0-9+.-]*:", lowered):
        scheme_part = lowered.split(":", 1)[0]
        if scheme_part not in _ALLOWED_SCHEMES:
            raise SsrfBlockedError(
                f"Blocked URL scheme '{scheme_part}://' — only http and https are allowed",
                url=raw,
            )

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise SsrfBlockedError(
            f"Blocked URL scheme '{scheme or '(empty)'}' — only http and https are allowed",
            url=raw,
        )

    host = (parsed.hostname or "").strip()
    if not host:
        raise SsrfBlockedError("URL must include a hostname", url=raw)

    if _hostname_looks_local(host) and not allow_private:
        raise SsrfBlockedError(
            f"Blocked host '{host}' — loopback/metadata/local names are not allowed",
            url=raw,
        )

    ip_lit = _parse_ip_literal(host)
    if ip_lit is not None and not allow_private and _is_blocked_ip(ip_lit):
        raise SsrfBlockedError(
            f"Blocked IP address '{host}' — private/loopback/link-local addresses are not allowed",
            url=raw,
        )

    # Skip DNS under pytest (unit tests mock HTTP; hostnames need not resolve).
    # Still block IP literals, localhost names, and bad schemes.
    if resolve_dns and os.environ.get("PYTEST_CURRENT_TEST"):
        resolve_dns = False
    if resolve_dns:
        try:
            from app.config import settings as _settings

            if getattr(_settings, "ENV", "") == "test":
                resolve_dns = False
            if not bool(getattr(_settings, "HTTP_AGENT_SSRF_RESOLVE_DNS", True)):
                resolve_dns = False
        except Exception:
            pass

    if resolve_dns and ip_lit is None and not allow_private:
        try:
            infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise SsrfBlockedError(
                f"Cannot resolve host '{host}': {exc}",
                url=raw,
            ) from exc
        for info in infos:
            sockaddr = info[4]
            addr = sockaddr[0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if _is_blocked_ip(ip):
                raise SsrfBlockedError(
                    f"Host '{host}' resolves to blocked address {addr} "
                    f"(private/loopback/link-local not allowed)",
                    url=raw,
                )

    return raw


def is_url_safe_for_http_agent(url: str, *, allow_private: bool = False) -> tuple[bool, str]:
    """Non-raising check; returns (ok, error_message)."""
    try:
        validate_http_agent_url(url, allow_private=allow_private)
        return True, ""
    except SsrfBlockedError as exc:
        return False, str(exc)
