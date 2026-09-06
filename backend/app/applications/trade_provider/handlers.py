# AgentFlow Intelligence v2.0 — Trade Application Tool Provider
"""Mock local handlers for trade application tools (no CRM / email delivery)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CUSTOMERS_CACHE: list[dict[str, Any]] | None = None
_CUSTOMERS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "trade" / "customers.json"
)


def _load_customers() -> list[dict[str, Any]]:
    global _CUSTOMERS_CACHE
    if _CUSTOMERS_CACHE is None:
        with _CUSTOMERS_PATH.open(encoding="utf-8") as handle:
            _CUSTOMERS_CACHE = json.load(handle)
    return _CUSTOMERS_CACHE


def search_customer(product: str, country: str | None = None) -> list[dict[str, Any]]:
    """Filter trade customers by product substring and optional country."""
    needle = (product or "").strip()
    if not needle:
        return []

    country_filter = (country or "").strip()
    needle_lower = needle.lower()
    results: list[dict[str, Any]] = []

    for customer in _load_customers():
        if country_filter and customer.get("country", "").lower() != country_filter.lower():
            continue

        matched_products = [
            item
            for item in customer.get("products", [])
            if needle_lower in str(item).lower()
        ]
        if not matched_products:
            continue

        match_reason = (
            f"product substring '{needle}' matched {matched_products!r} "
            f"for {customer.get('company', 'unknown')}"
        )
        if country_filter:
            match_reason += f" in country '{country_filter}'"

        results.append(
            {
                **customer,
                "match_reason": match_reason,
            }
        )

    return results


def trade_search_customer_handler(
    *,
    product: str = "",
    country: str | None = None,
) -> list[dict[str, Any]]:
    """Local handler entrypoint for ``trade.search_customer``."""
    return search_customer(product=product, country=country)


def trade_generate_email_handler(
    *,
    customer: str = "",
    product: str = "",
    language: str = "en",
) -> dict[str, str]:
    """Return a mock outbound email draft for ``trade.generate_email``."""
    subject = f"Partnership opportunity: {product} for {customer}"
    body = (
        f"Dear {customer},\n\n"
        f"We would like to introduce our {product} solution to your organization.\n"
        f"(Draft language: {language})\n"
    )
    return {"subject": subject, "body": body}
