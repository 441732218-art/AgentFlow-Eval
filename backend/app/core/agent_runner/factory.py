"""Agent runner factory — select OpenAI ReAct, HTTP, or plugin runners."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_agent_runner(agent_config: dict[str, Any] | None = None) -> Any:
    """按 agent_config.runner 构造 openai / http / 插件 Runner。"""
    from app.config import settings as app_settings

    cfg = dict(agent_config or {})
    runner_type = str(cfg.get("runner") or cfg.get("type") or "openai").lower().strip()

    # 插件 runner 优先
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

    api_key = cfg.get("api_key") or app_settings.OPENAI_API_KEY or None
    base_url = cfg.get("base_url") or app_settings.OPENAI_BASE_URL or None
    try:
        timeout_seconds = float(
            cfg.get("timeout_seconds")
            or cfg.get("timeout")
            or getattr(app_settings, "LLM_CALL_TIMEOUT_SEC", 30.0)
            or 30.0
        )
    except (TypeError, ValueError):
        timeout_seconds = 30.0
    try:
        temperature = float(cfg.get("temperature", 0.0))
    except (TypeError, ValueError):
        temperature = 0.0
    try:
        max_tokens = int(cfg.get("max_tokens", 0) or 0)
    except (TypeError, ValueError):
        max_tokens = 0

    return OpenAIReActRunner(
        api_key=api_key,
        base_url=base_url,
        model=cfg.get("model", "gpt-4o-mini"),
        max_iterations=int(cfg.get("max_iterations", 5)),
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens or None,
        provider=str(cfg.get("provider") or "openai").lower().strip() or "openai",
    )
