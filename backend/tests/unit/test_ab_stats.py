# (c) 2026 AgentFlow-Eval
"""Unit tests for A/B statistics and sticky assignment."""

from __future__ import annotations

from app.core.ab.assignment import VariantWeight, assign_variant, stable_bucket
from app.core.ab.stats import (
    sample_size_proportion,
    two_proportion_z_test,
    welch_t_test,
)


class TestAssignment:
    def test_sticky(self):
        variants = [
            VariantWeight("control", 1.0),
            VariantWeight("treatment", 1.0),
        ]
        a = assign_variant("exp1", "user-42", variants)
        b = assign_variant("exp1", "user-42", variants)
        assert a == b

    def test_bucket_range(self):
        b = stable_bucket("e", "u", buckets=1000)
        assert 0 <= b < 1000

    def test_weight_skew(self):
        variants = [
            VariantWeight("a", 9.0),
            VariantWeight("b", 1.0),
        ]
        counts = {"a": 0, "b": 0}
        for i in range(2000):
            v = assign_variant("skew", f"u{i}", variants)
            counts[v] += 1
        # ~90/10 — allow wide margin
        assert counts["a"] > counts["b"]
        assert counts["a"] / 2000 > 0.75


class TestStats:
    def test_proportion_significant(self):
        # Large sample clear lift
        r = two_proportion_z_test(100, 1000, 150, 1000, alpha=0.05)
        assert r.treatment_rate > r.control_rate
        assert r.p_value < 0.05
        assert r.significant is True

    def test_proportion_no_sample(self):
        r = two_proportion_z_test(0, 0, 0, 0)
        assert r.p_value == 1.0
        assert r.significant is False

    def test_welch_identical(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        r = welch_t_test(vals, vals)
        assert abs(r.t_stat) < 1e-9
        assert r.p_value > 0.5

    def test_welch_different(self):
        a = [1.0, 1.1, 0.9, 1.0, 1.05] * 20
        b = [2.0, 2.1, 1.9, 2.0, 2.05] * 20
        r = welch_t_test(a, b)
        assert r.significant is True
        assert r.absolute_lift > 0

    def test_sample_size(self):
        n = sample_size_proportion(0.1, 0.02, alpha=0.05, power=0.8)
        assert n > 100
