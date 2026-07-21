# (c) 2026 AgentFlow-Eval
"""Agent runner factory — select OpenAI ReAct, HTTP, or plugin runners."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_agent_runner(agent_config: dict[str, Any] | None = None) -> Any:
    """Build an agent runner from task ``agent_config``.

    Supported ``runner`` values:
      - ``openai`` / ``react`` / omitted — OpenAIReActRunner (default)
      - ``http`` / ``http_agent`` — HttpAgentRunner
      - any key registered by an active **plugin** (e.g. ``echo``)

    HTTP config keys (when runner=http)::

        {
          "runner": "http",
          "endpoint_url": "https://agent.example.com/v1/run",
          "timeout_sec": 60,
          "headers": {"Authorization": "Bearer ..."},
          "method": "POST",
          "context": {"tenant": "acme"},
          "verify_ssl": true
        }

    OpenAI config keys::

        {
          "runner": "openai",
          "model": "gpt-4o-mini",
          "max_iterations": 5
        }

    Args:
        agent_config: Task-level agent configuration dict.

    Returns:
        Runner instance with async ``run(query, tools=...)`` method.
    """
    from app.config import settings as app_settings

    cfg = dict(agent_config or {})
    runner_type = str(cfg.get("runner") or cfg.get("type") or "openai").lower().strip()

    # Plugin-registered runners take precedence for non-built-in keys, and can
    # also override if explicitly registered under the same name.
    try:
        from app.core.plugins.registry import get_capability_registry

        plugin_factory = get_capability_registry().get_runner_factory(runner_type)
        if plugin_factory is not None:
            logger.debug("Using plugin agent runner: %s", runner_type)
            return plugin_factory(cfg)
    except Exception as exc:
        logger.debug("Plugin runner lookup skipped: %s", exc)

    if runner_type in {"http", "http_agent", "remote", "webhook"}:
        from app.core.agent_runner.http_runner import HttpAgentRunner

        endpoint = (
            cfg.get("endpoint_url") or cfg.get("url") or cfg.get("endpoint") or ""
        )
        headers = cfg.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        return HttpAgentRunner(
            endpoint_url=str(endpoint),
            timeout_sec=float(cfg.get("timeout_sec") or cfg.get("timeout") or 60.0),
            headers={str(k): str(v) for k, v in headers.items()},
            method=str(cfg.get("method") or "POST"),
            context=cfg.get("context") if isinstance(cfg.get("context"), dict) else {},
            verify_ssl=bool(cfg.get("verify_ssl", True)),
        )

    from app.core.agent_runner.openai_runner import OpenAIReActRunner

    return OpenAIReActRunner(
        api_key=app_settings.OPENAI_API_KEY or None,
        base_url=app_settings.OPENAI_BASE_URL or None,
        model=cfg.get("model", "gpt-4o-mini"),
        max_iterations=int(cfg.get("max_iterations", 5)),
    )
