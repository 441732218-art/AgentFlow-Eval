# (c) 2026 AgentFlow-Eval
"""Sticky traffic assignment for A/B variants."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class VariantWeight:
    """Variant label + traffic weight (relative)."""

    key: str
    weight: float = 1.0


def stable_bucket(experiment_key: str, unit_id: str, *, buckets: int = 10_000) -> int:
    """Deterministic bucket in [0, buckets) for sticky assignment."""
    raw = f"{experiment_key}::{unit_id}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:12], 16) % buckets


def assign_variant(
    experiment_key: str,
    unit_id: str,
    variants: Sequence[VariantWeight],
    *,
    buckets: int = 10_000,
) -> str:
    """Pick a variant key using weighted sticky hashing.

    Weights are relative (e.g. 50/50 or 90/10). Zero/negative weights are ignored.
    """
    active = [v for v in variants if v.weight > 0 and v.key]
    if not active:
        raise ValueError("no active variants with positive weight")
    total = sum(v.weight for v in active)
    # Map bucket → cumulative weight interval
    b = stable_bucket(experiment_key, unit_id, buckets=buckets)
    # Position in [0, total)
    pos = (b / buckets) * total
    acc = 0.0
    for v in active:
        acc += v.weight
        if pos < acc:
            return v.key
    return active[-1].key
