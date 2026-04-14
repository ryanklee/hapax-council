"""Bayesian analysis functions for conversational continuity proofs.

Pure functions for sequential hypothesis testing and correlation analysis
across SCED experiment phases. Uses scipy.special for Beta CDF to avoid
the scipy.stats init crash with torch (scipy 1.17 + torch compatibility issue).

LRR Phase 1 item 7 verification (2026-04-14):
- The original analysis stack is **beta-binomial** (`bayes_factor`,
  `rope_check`) — appropriate for binary success/failure proportions
  but not for continuous behavioral metrics like grounding act counts.
- Bundle 2 §1 calls for **BEST** (Bayesian Estimation Supersedes the
  t-test, Kruschke 2013) for continuous group comparisons. The
  canonical Kruschke implementation uses PyMC + MCMC; council does
  not currently have PyMC as a dependency.
- This file ships a **scipy-only analytical BEST approximation**
  (`best_two_sample`) appropriate for Phase 1 + 2 + 3 work. The
  approximation uses Welch's t-test + a normal approximation for the
  posterior over the difference of means, and reports the same dict
  shape as Bundle 2's canonical `report_best`. **Phase 4 baseline
  collection should upgrade to MCMC-BEST** before any claim is filed.
- DEVIATION-NNN: if Phase 4 needs the canonical MCMC version, file a
  deviation against this file when adding the PyMC dependency. The
  approximation here is a known-good interim, not a substitute.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.special import betainc


def _beta_cdf(x: float, a: float, b: float) -> float:
    """CDF of Beta(a, b) at x, using regularized incomplete beta function."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return float(betainc(a, b, x))


def _norm_pdf(x: float, loc: float = 0.0, scale: float = 1.0) -> float:
    """PDF of Normal(loc, scale) at x."""
    z = (x - loc) / scale
    return float(np.exp(-0.5 * z * z) / (scale * math.sqrt(2 * math.pi)))


def _pearsonr(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient."""
    ax = np.array(x, dtype=np.float64)
    ay = np.array(y, dtype=np.float64)
    ax_m = ax - ax.mean()
    ay_m = ay - ay.mean()
    num = float(np.sum(ax_m * ay_m))
    den = float(np.sqrt(np.sum(ax_m**2) * np.sum(ay_m**2)))
    if den < 1e-12:
        return 0.0
    return num / den


def bayes_factor(
    successes: int,
    trials: int,
    prior_a: float = 2.0,
    prior_b: float = 2.0,
    rope_low: float = 0.45,
    rope_high: float = 0.55,
) -> float:
    """Beta-binomial Bayes Factor: mass outside ROPE / mass inside ROPE.

    Posterior = Beta(prior_a + successes, prior_b + failures).
    BF = P(theta outside ROPE | data) / P(theta inside ROPE | data).
    """
    failures = trials - successes
    post_a = prior_a + successes
    post_b = prior_b + failures

    mass_inside = _beta_cdf(rope_high, post_a, post_b) - _beta_cdf(rope_low, post_a, post_b)
    mass_outside = 1.0 - mass_inside

    if mass_inside < 1e-12:
        return float("inf")
    return mass_outside / mass_inside


def sequential_check(
    bf: float,
    n: int,
    max_n: int,
    bf_threshold: float = 10.0,
) -> str:
    """Sequential stopping rule for Bayesian SCED.

    Returns "continue", "stop_h1", "stop_h0", or "stop_max".
    """
    if n >= max_n:
        return "stop_max"
    if bf >= bf_threshold:
        return "stop_h1"
    if bf <= 1.0 / bf_threshold:
        return "stop_h0"
    return "continue"


def rope_check(
    successes: int,
    trials: int,
    prior_a: float = 2.0,
    prior_b: float = 2.0,
    rope_low: float = 0.45,
    rope_high: float = 0.55,
) -> dict[str, float]:
    """Posterior mass inside and outside ROPE.

    Returns {"inside": float, "outside": float}.
    """
    failures = trials - successes
    post_a = prior_a + successes
    post_b = prior_b + failures

    mass_inside = _beta_cdf(rope_high, post_a, post_b) - _beta_cdf(rope_low, post_a, post_b)
    return {"inside": mass_inside, "outside": 1.0 - mass_inside}


def bayes_correlation(
    x: list[float],
    y: list[float],
    prior_mu: float = 0.0,
    prior_sigma: float = 1.0,
) -> dict[str, float]:
    """Bayesian correlation: Pearson r → Fisher z → Normal prior update.

    Returns {"r", "posterior_mu", "posterior_sigma", "bf", "ci_95"}.
    """
    n = len(x)
    r = _pearsonr(x, y)

    # Fisher z-transform
    z_obs = math.atanh(max(-0.9999, min(0.9999, r)))
    se = 1.0 / math.sqrt(n - 3) if n > 3 else 1.0

    # Normal-Normal conjugate update
    prior_prec = 1.0 / (prior_sigma**2)
    data_prec = 1.0 / (se**2)
    post_prec = prior_prec + data_prec
    post_sigma = math.sqrt(1.0 / post_prec)
    post_mu = (prior_prec * math.atanh(prior_mu) + data_prec * z_obs) / post_prec

    # Back-transform posterior mean to r scale
    post_r = math.tanh(post_mu)

    # 95% CI in z-space, back-transformed
    ci_z_low = post_mu - 1.96 * post_sigma
    ci_z_high = post_mu + 1.96 * post_sigma
    ci_95 = (math.tanh(ci_z_low), math.tanh(ci_z_high))

    # Savage-Dickey BF at r=0 (z=0)
    prior_density_at_0 = _norm_pdf(0, loc=math.atanh(prior_mu), scale=prior_sigma)
    post_density_at_0 = _norm_pdf(0, loc=post_mu, scale=post_sigma)
    bf = prior_density_at_0 / post_density_at_0 if post_density_at_0 > 1e-12 else float("inf")

    return {
        "r": r,
        "posterior_mu": post_r,
        "posterior_sigma": post_sigma,
        "bf": bf,
        "ci_95": ci_95,
    }


def baseline_corrected_tau(
    baseline: list[float],
    intervention: list[float],
) -> dict[str, float]:
    """Baseline Corrected Tau (BCTau) for SCED effect size.

    Corrects for monotonic baseline trend using Theil-Sen estimator,
    then computes Kendall's Tau-like non-overlap statistic.
    Bounded [-1, +1]. Standard SCED effect size (Tarlow 2017).

    Returns {"tau", "p_value", "baseline_slope", "n_baseline", "n_intervention"}.
    """
    import numpy as np

    n_a = len(baseline)
    n_b = len(intervention)

    if n_a < 3 or n_b < 3:
        return {
            "tau": 0.0,
            "p_value": 1.0,
            "baseline_slope": 0.0,
            "n_baseline": n_a,
            "n_intervention": n_b,
        }

    # Theil-Sen slope of baseline trend
    slopes: list[float] = []
    for i in range(n_a):
        for j in range(i + 1, n_a):
            if j != i:
                slopes.append((baseline[j] - baseline[i]) / (j - i))
    baseline_slope = float(np.median(slopes)) if slopes else 0.0

    # Detrend: subtract expected trend from both phases
    detrended_a = [baseline[i] - baseline_slope * i for i in range(n_a)]
    detrended_b = [intervention[i] - baseline_slope * (n_a + i) for i in range(n_b)]

    # Non-overlap: count pairs where intervention > baseline
    concordant = 0
    discordant = 0
    ties = 0
    for a_val in detrended_a:
        for b_val in detrended_b:
            if b_val > a_val:
                concordant += 1
            elif b_val < a_val:
                discordant += 1
            else:
                ties += 1

    total_pairs = n_a * n_b
    tau = (concordant - discordant) / total_pairs if total_pairs > 0 else 0.0

    # Approximate p-value (normal approximation for Mann-Whitney U)
    u = concordant
    mu_u = n_a * n_b / 2
    sigma_u = math.sqrt(n_a * n_b * (n_a + n_b + 1) / 12) if (n_a + n_b) > 1 else 1.0
    z = (u - mu_u) / sigma_u if sigma_u > 0 else 0.0
    # Two-tailed p from z
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))

    return {
        "tau": round(tau, 4),
        "p_value": round(p_value, 4),
        "baseline_slope": round(baseline_slope, 4),
        "n_baseline": n_a,
        "n_intervention": n_b,
    }


# ----------------------------------------------------------------------------
# LRR Phase 1 item 7 — BEST two-sample comparison (analytical approximation)
# ----------------------------------------------------------------------------

BEST_METHOD_LABEL = "scipy-analytical-approx-2026-04-14"
"""Label written into the result dict so future analyses can detect which
implementation produced the numbers. Phase 4 may upgrade to MCMC-BEST and
this label will change to e.g. ``pymc-mcmc-2026-04-XX`` so historical
comparisons can re-run analyses against the new implementation."""


def best_two_sample(
    group_a: list[float] | np.ndarray,
    group_b: list[float] | np.ndarray,
    rope_effect_size: tuple[float, float] = (-0.1, 0.1),
) -> dict[str, Any]:
    """Bayesian two-sample comparison — analytical approximation of BEST.

    Per Bundle 2 §1, the canonical BEST implementation uses PyMC + MCMC
    sampling (Kruschke 2013). Council does not currently have PyMC as a
    dependency, so this function ships a scipy-only analytical
    approximation appropriate for Phase 1 + 2 + 3 LRR work. **Phase 4
    baseline collection should upgrade to MCMC-BEST** before any claim
    is filed (see DEVIATION procedure in module docstring).

    Approach:
        1. Welch's two-sample setup: pooled variance + degrees of freedom
        2. Approximate the posterior over (mu_b - mu_a) as a Normal centered
           on the observed difference with std = Welch standard error
        3. Approximate effect size posterior via Normal(d_obs, se_d) where
           d_obs is Cohen's d and se_d is the conventional sampling SE
        4. Report 95% HDI as ±1.96·SE around the mean (HDI of a Normal
           equals the equal-tailed CI when the distribution is symmetric)
        5. P(diff > 0) and P(effect outside ROPE) computed via normal CDF

    The result dict shape matches Bundle 2's canonical ``report_best``
    output so future MCMC-BEST upgrades drop in cleanly. The
    ``BEST_METHOD_LABEL`` field lets downstream consumers detect which
    implementation produced the numbers.

    Args:
        group_a: 1D array of metric values from Condition A
        group_b: 1D array of metric values from Condition B
        rope_effect_size: ROPE bounds for Cohen's d (default ±0.1 per Kruschke)

    Returns:
        Dict with method, n_a, n_b, diff_means_*, effect_size_*,
        p_diff_means_positive, p_effect_outside_rope_*. NaN-safe: if either
        group is empty or pooled variance is zero, returns a sentinel dict
        with method=BEST_METHOD_LABEL and all numeric fields set to None.
    """
    a = np.asarray(group_a, dtype=np.float64)
    b = np.asarray(group_b, dtype=np.float64)
    n_a = len(a)
    n_b = len(b)
    if n_a < 2 or n_b < 2:
        return _best_sentinel(n_a, n_b, "insufficient sample size (need n >= 2 per group)")

    mean_a = float(a.mean())
    mean_b = float(b.mean())
    var_a = float(a.var(ddof=1))
    var_b = float(b.var(ddof=1))
    if var_a <= 0 and var_b <= 0:
        return _best_sentinel(n_a, n_b, "pooled variance is zero (both groups constant)")

    diff_obs = mean_b - mean_a

    # Welch standard error for the difference of means
    se_diff = math.sqrt(var_a / n_a + var_b / n_b)

    # Cohen's d (pooled SD), with sampling SE per Hedges-Olkin
    pooled_sd = math.sqrt((var_a + var_b) / 2.0)
    if pooled_sd <= 0:
        return _best_sentinel(n_a, n_b, "pooled SD is zero")
    d_obs = diff_obs / pooled_sd
    se_d = math.sqrt((n_a + n_b) / (n_a * n_b) + d_obs**2 / (2 * (n_a + n_b)))

    # 95% HDI (= equal-tailed 95% CI for a symmetric Normal posterior)
    z95 = 1.959963984540054  # scipy.stats.norm.ppf(0.975)
    diff_hdi_lo = diff_obs - z95 * se_diff
    diff_hdi_hi = diff_obs + z95 * se_diff
    effect_hdi_lo = d_obs - z95 * se_d
    effect_hdi_hi = d_obs + z95 * se_d

    # P(diff > 0) under Normal(diff_obs, se_diff)
    # Z-score for diff_obs > 0 → P = Phi(diff_obs / se_diff)
    p_diff_positive = (
        _normal_cdf(diff_obs / se_diff) if se_diff > 0 else (1.0 if diff_obs > 0 else 0.0)
    )

    # P(effect outside ROPE) under Normal(d_obs, se_d)
    rope_lo, rope_hi = rope_effect_size
    if se_d > 0:
        p_below_rope = _normal_cdf((rope_lo - d_obs) / se_d)
        p_above_rope = 1.0 - _normal_cdf((rope_hi - d_obs) / se_d)
        p_outside_rope = p_below_rope + p_above_rope
    else:
        p_outside_rope = 0.0 if rope_lo <= d_obs <= rope_hi else 1.0

    return {
        "method": BEST_METHOD_LABEL,
        "ref": "Kruschke 2013 (analytical approx; canonical MCMC pending Phase 4 PyMC dep)",
        "n_a": n_a,
        "n_b": n_b,
        "diff_means_mean": diff_obs,
        "diff_means_hdi95": [diff_hdi_lo, diff_hdi_hi],
        "diff_means_se": se_diff,
        "effect_size_mean": d_obs,
        "effect_size_hdi95": [effect_hdi_lo, effect_hdi_hi],
        "effect_size_se": se_d,
        "p_diff_means_positive": float(p_diff_positive),
        "p_effect_outside_rope_neg10_pos10": float(p_outside_rope),
        "rope_used": list(rope_effect_size),
    }


def _best_sentinel(n_a: int, n_b: int, reason: str) -> dict[str, Any]:
    """Return a None-filled BEST result dict when input is invalid."""
    return {
        "method": BEST_METHOD_LABEL,
        "ref": "Kruschke 2013 (analytical approx)",
        "n_a": n_a,
        "n_b": n_b,
        "diff_means_mean": None,
        "diff_means_hdi95": None,
        "diff_means_se": None,
        "effect_size_mean": None,
        "effect_size_hdi95": None,
        "effect_size_se": None,
        "p_diff_means_positive": None,
        "p_effect_outside_rope_neg10_pos10": None,
        "rope_used": None,
        "error": reason,
    }


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via math.erf (avoids scipy.stats import)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
