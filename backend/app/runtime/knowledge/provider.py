# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Knowledge provider interface for Agent Runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class KnowledgeProvider(ABC):
    """Abstract knowledge retrieval for agent context enrichment."""

    @abstractmethod
    async def query(self, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant knowledge chunks for a query."""
