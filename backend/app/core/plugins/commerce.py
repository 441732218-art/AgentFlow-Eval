# (c) 2026 AgentFlow-Eval
"""Plugin marketplace commerce metadata + entitlement checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PluginCommerceMeta:
    """Commercial listing attributes for a plugin."""

    price_cents: int = 0
    currency: str = "USD"
    license: str = "MIT"  # MIT | proprietary | dual
    entitlement_plan: list[str] = field(
        default_factory=lambda: ["free", "pro", "enterprise"]
    )
    trial_days: int = 0
    is_paid: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["is_paid"] = self.price_cents > 0 or self.is_paid
        return d

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "PluginCommerceMeta":
        data = data or {}
        price = int(data.get("price_cents") or 0)
        return cls(
            price_cents=price,
            currency=str(data.get("currency") or "USD"),
            license=str(data.get("license") or "MIT"),
            entitlement_plan=list(
                data.get("entitlement_plan") or ["free", "pro", "enterprise"]
            ),
            trial_days=int(data.get("trial_days") or 0),
            is_paid=bool(data.get("is_paid") or price > 0),
        )


def check_entitlement(
    commerce: PluginCommerceMeta,
    *,
    plan_code: str | None,
    plan_features: dict[str, Any] | None = None,
    plugin_id: str = "",
) -> tuple[bool, str]:
    """Whether current plan may install/activate the plugin."""
    plan = (plan_code or "free").lower()
    if commerce.price_cents <= 0 and not commerce.is_paid:
        # free plugin — still respect plan plugin allow-list if present
        if plan_features:
            from app.core.billing.service import get_billing_service

            if not get_billing_service().plan_allows_plugin(plan_features, plugin_id):
                return False, f"plan {plan} does not include plugin {plugin_id}"
        return True, "free plugin"
    if plan in {p.lower() for p in commerce.entitlement_plan}:
        return True, f"plan {plan} entitled"
    if plan_features and plan_features.get("plugins") in (["*"], "*"):
        return True, "wildcard plugins"
    return False, f"plan {plan} not in entitlement_plan={commerce.entitlement_plan}"
