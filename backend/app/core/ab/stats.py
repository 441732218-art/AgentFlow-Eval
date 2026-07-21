# (c) 2026 AgentFlow-Eval
"""Statistical tests for A/B experiments (no scipy required)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ProportionTestResult:
    """Two-proportion z-test (e.g. conversion rate A vs B)."""

    control_n: int
    control_successes: int
    treatment_n: int
    treatment_successes: int
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float | None
    z_stat: float
    p_value: float
    ci95_low: float
    ci95_high: float
    significant: bool
    alpha: float

    def to_dict(self) -> dict:
        return {
            "test": "two_proportion_z",
            "control_n": self.control_n,
            "control_successes": self.control_successes,
            "treatment_n": self.treatment_n,
            "treatment_successes": self.treatment_successes,
            "control_rate": round(self.control_rate, 6),
            "treatment_rate": round(self.treatment_rate, 6),
            "absolute_lift": round(self.absolute_lift, 6),
            "relative_lift": (
                round(self.relative_lift, 6) if self.relative_lift is not None else None
            ),
            "z_stat": round(self.z_stat, 4),
            "p_value": round(self.p_value, 6),
            "ci95_lift": [round(self.ci95_low, 6), round(self.ci95_high, 6)],
            "significant": self.significant,
            "alpha": self.alpha,
        }


@dataclass(frozen=True)
class MeanTestResult:
    """Welch's t-test for continuous metrics (e.g. score, latency)."""

    control_n: int
    treatment_n: int
    control_mean: float
    treatment_mean: float
    control_std: float
    treatment_std: float
    absolute_lift: float
    relative_lift: float | None
    t_stat: float
    df: float
    p_value: float
    significant: bool
    alpha: float

    def to_dict(self) -> dict:
        return {
            "test": "welch_t",
            "control_n": self.control_n,
            "treatment_n": self.treatment_n,
            "control_mean": round(self.control_mean, 4),
            "treatment_mean": round(self.treatment_mean, 4),
            "control_std": round(self.control_std, 4),
            "treatment_std": round(self.treatment_std, 4),
            "absolute_lift": round(self.absolute_lift, 4),
            "relative_lift": (
                round(self.relative_lift, 6) if self.relative_lift is not None else None
            ),
            "t_stat": round(self.t_stat, 4),
            "df": round(self.df, 2),
            "p_value": round(self.p_value, 6),
            "significant": self.significant,
            "alpha": self.alpha,
        }


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Approximate inverse normal CDF (Acklam / Beasley-Springer style)."""
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")
    # Coefficients for rational approximation
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def two_proportion_z_test(
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    *,
    alpha: float = 0.05,
) -> ProportionTestResult:
    """Two-sided two-proportion z-test with CI on absolute rate difference."""
    n1, n2 = max(0, control_n), max(0, treatment_n)
    x1, x2 = max(0, control_successes), max(0, treatment_successes)
    p1 = x1 / n1 if n1 else 0.0
    p2 = x2 / n2 if n2 else 0.0
    abs_lift = p2 - p1
    rel_lift = (abs_lift / p1) if p1 > 0 else None

    if n1 == 0 or n2 == 0:
        return ProportionTestResult(
            control_n=n1,
            control_successes=x1,
            treatment_n=n2,
            treatment_successes=x2,
            control_rate=p1,
            treatment_rate=p2,
            absolute_lift=abs_lift,
            relative_lift=rel_lift,
            z_stat=0.0,
            p_value=1.0,
            ci95_low=abs_lift,
            ci95_high=abs_lift,
            significant=False,
            alpha=alpha,
        )

    # Pooled SE for H0: p1 == p2
    p_pool = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(max(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2), 1e-18))
    z = (p2 - p1) / se_pool if se_pool > 0 else 0.0
    p_value = 2 * (1 - _norm_cdf(abs(z)))

    # Unpooled SE for CI on difference
    se_unpooled = math.sqrt(
        max(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2, 1e-18)
    )
    z_crit = _norm_ppf(1 - alpha / 2)
    ci_low = abs_lift - z_crit * se_unpooled
    ci_high = abs_lift + z_crit * se_unpooled

    return ProportionTestResult(
        control_n=n1,
        control_successes=x1,
        treatment_n=n2,
        treatment_successes=x2,
        control_rate=p1,
        treatment_rate=p2,
        absolute_lift=abs_lift,
        relative_lift=rel_lift,
        z_stat=z,
        p_value=p_value,
        ci95_low=ci_low,
        ci95_high=ci_high,
        significant=p_value < alpha,
        alpha=alpha,
    )


def _mean_std(values: Sequence[float]) -> tuple[float, float, int]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0
    m = sum(values) / n
    if n == 1:
        return m, 0.0, 1
    var = sum((x - m) ** 2 for x in values) / (n - 1)
    return m, math.sqrt(max(var, 0.0)), n


def _t_sf_approx(t: float, df: float) -> float:
    """Two-sided p-value for Student's t via normal approx for large df,
    and simple regularized incomplete beta for moderate df.
    """
    if df <= 0:
        return 1.0
    # For large df, normal approximation is fine
    if df > 100:
        return 2 * (1 - _norm_cdf(abs(t)))
    # Hill's approximation of t CDF (via normal adj using df/(df+t^2))
    # incomplete beta I_x(df/2, 0.5) ≈ continued fraction lite via erf transform
    # Use: p ≈ 2 * (1 - Phi(t * sqrt(1 - 1/(4df)))) rough
    adj = abs(t) * math.sqrt(df / (df + t * t) * (1 - 1 / (4 * df)))
    return max(0.0, min(1.0, 2 * (1 - _norm_cdf(adj))))


def welch_t_test(
    control: Sequence[float],
    treatment: Sequence[float],
    *,
    alpha: float = 0.05,
) -> MeanTestResult:
    """Two-sided Welch's t-test for unequal variances."""
    m1, s1, n1 = _mean_std(list(control))
    m2, s2, n2 = _mean_std(list(treatment))
    abs_lift = m2 - m1
    rel_lift = (abs_lift / m1) if m1 != 0 else None

    if n1 < 2 or n2 < 2:
        return MeanTestResult(
            control_n=n1,
            treatment_n=n2,
            control_mean=m1,
            treatment_mean=m2,
            control_std=s1,
            treatment_std=s2,
            absolute_lift=abs_lift,
            relative_lift=rel_lift,
            t_stat=0.0,
            df=0.0,
            p_value=1.0,
            significant=False,
            alpha=alpha,
        )

    v1, v2 = s1 * s1, s2 * s2
    se = math.sqrt(v1 / n1 + v2 / n2)
    t_stat = (m2 - m1) / se if se > 0 else 0.0
    # Welch–Satterthwaite df
    num = (v1 / n1 + v2 / n2) ** 2
    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = num / den if den > 0 else float(n1 + n2 - 2)
    p_value = _t_sf_approx(t_stat, df)

    return MeanTestResult(
        control_n=n1,
        treatment_n=n2,
        control_mean=m1,
        treatment_mean=m2,
        control_std=s1,
        treatment_std=s2,
        absolute_lift=abs_lift,
        relative_lift=rel_lift,
        t_stat=t_stat,
        df=df,
        p_value=p_value,
        significant=p_value < alpha,
        alpha=alpha,
    )


def sample_size_proportion(
    baseline_rate: float,
    mde: float,
    *,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """Per-variant sample size for two-proportion test (two-sided).

    Args:
        baseline_rate: Control conversion rate (0–1).
        mde: Minimum detectable absolute effect size.
        alpha: Type I error.
        power: 1 - Type II error.
    """
    p1 = min(max(baseline_rate, 1e-6), 1 - 1e-6)
    p2 = min(max(p1 + mde, 1e-6), 1 - 1e-6)
    z_a = _norm_ppf(1 - alpha / 2)
    z_b = _norm_ppf(power)
    p_bar = (p1 + p2) / 2
    num = (
        z_a * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    den = (p2 - p1) ** 2
    if den <= 0:
        return 0
    return int(math.ceil(num / den))
