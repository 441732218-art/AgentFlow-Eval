# AgentFlow Intelligence v2.0 — Trade Application Tool Provider
"""Input contract types for trade application tools (documentation / validation)."""

from __future__ import annotations

from typing import TypedDict


class SearchCustomerInput(TypedDict, total=False):
    """Arguments for ``trade.search_customer``."""

    keyword: str
    country: str


class GenerateEmailInput(TypedDict, total=False):
    """Arguments for ``trade.generate_email``."""

    customer: str
    product: str
    language: str


class CreateFollowupInput(TypedDict, total=False):
    """Arguments for ``trade.create_followup``."""

    customer_id: str
    stage: str
