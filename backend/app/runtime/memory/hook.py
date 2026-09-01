# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Memory hook integrating ``MemoryProvider`` with the execution pipeline."""

from __future__ import annotations

import logging
from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.memory.provider import MemoryProvider
from app.runtime.pipeline.hooks import ExecutionHook

logger = logging.getLogger(__name__)

MEMORY_DATA_KEY = "memory_data"


class MemoryHook(ExecutionHook):
    """Load and update agent/session memory via ``MemoryProvider`` (fail-safe)."""

    def __init__(self, memory_provider: MemoryProvider) -> None:
        self.memory_provider = memory_provider

    def before_execute(self, context: RuntimeContext, task: str) -> None:
        _ = task
        memory_key = context.metadata.get("memory_key")
        if not memory_key:
            return
        try:
            value = self.memory_provider.get(str(memory_key))
            if value is not None:
                context.metadata[MEMORY_DATA_KEY] = value
        except Exception:
            logger.exception(
                "MemoryHook.before_execute failed for key=%r", memory_key
            )

    def after_execute(self, context: RuntimeContext, result: Any) -> None:
        memory_key = context.metadata.get("memory_key")
        if not memory_key:
            return
        try:
            self.memory_provider.set(str(memory_key), result)
        except Exception:
            logger.exception(
                "MemoryHook.after_execute failed for memory_key=%r", memory_key
            )
