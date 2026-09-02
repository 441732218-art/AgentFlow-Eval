# AgentFlow Intelligence v2.0 — Example Application Tool Provider
"""Local handlers owned by the example application provider."""

from __future__ import annotations


def app_example_echo_handler(*, message: str = "") -> dict[str, str]:
    """Echo handler for ``app_example.echo``."""
    return {"app_echo": message}
