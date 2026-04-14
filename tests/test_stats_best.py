"""LRR Phase 1 item 7 — BEST analytical approximation smoke tests.

Per Bundle 2 §1, council's stats.py was beta-binomial only and needed a
BEST equivalent. This PR (Phase 1 PR #4) added `best_two_sample` as a
scipy-only analytical approximation. These tests verify:

1. The function returns a valid result dict on synthetic data with a
   known true difference
2. The 95% HDI brackets the true effect size
3. P(diff > 0) responds correctly to the sign of the true effect
4. P(effect outside ROPE) responds correctly to large vs small effects
5. NaN-safe sentinel behavior on edge cases (n < 2, zero variance)

Phase 4 will upgrade to canonical MCMC-BEST via PyMC. These tests will
need to be re-run against the new implementation; the dict shape is
fixed so the upgrade is drop-in.
"""

from __future__ import annotations

import numpy as np

from agents.hapax_daimonion.stats import BEST_METHOD_LABEL, best_two_sample


class TestBestTwoSampleHappyPath:
    def test_returns_dict_with_expected_keys(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(loc=0.0, scale=1.0, size=50)
        b = rng.normal(loc=0.5, scale=1.0, size=50)
        result = best_two_sample(a, b)
        for key in (
            "method",
            "ref",
            "n_a",
            "n_b",
            "diff_means_mean",
            "diff_means_hdi95",
            "diff_means_se",
            "effect_size_mean",
            "effect_size_hdi95",
            "effect_size_se",
            "p_diff_means_positive",
            "p_effect_outside_rope_neg10_pos10",
            "rope_used",
        ):
            assert key in result, f"missing key {key!r}"
        assert result["method"] == BEST_METHOD_LABEL

    def test_hdi_brackets_true_difference_for_known_effect(self):
        rng = np.random.default_rng(seed=42)
        # True difference of means = 1.0
        a = rng.normal(loc=0.0, scale=1.0, size=200)
        b = rng.normal(loc=1.0, scale=1.0, size=200)
        result = best_two_sample(a, b)
        lo, hi = result["diff_means_hdi95"]
        assert lo < 1.0 < hi, f"95% HDI [{lo:.3f}, {hi:.3f}] does not bracket true difference 1.0"

    def test_p_diff_positive_close_to_one_for_strong_positive_effect(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(loc=0.0, scale=1.0, size=200)
        b = rng.normal(loc=2.0, scale=1.0, size=200)
        result = best_two_sample(a, b)
        assert result["p_diff_means_positive"] > 0.99

    def test_p_diff_positive_close_to_zero_for_strong_negative_effect(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(loc=2.0, scale=1.0, size=200)
        b = rng.normal(loc=0.0, scale=1.0, size=200)
        result = best_two_sample(a, b)
        assert result["p_diff_means_positive"] < 0.01

    def test_p_effect_outside_rope_high_for_large_effect(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(loc=0.0, scale=1.0, size=200)
        b = rng.normal(loc=2.0, scale=1.0, size=200)
        result = best_two_sample(a, b)
        # Cohen's d ≈ 2 → way outside the [-0.1, 0.1] ROPE
        assert result["p_effect_outside_rope_neg10_pos10"] > 0.99

    def test_p_effect_outside_rope_low_for_null_effect(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(loc=0.0, scale=1.0, size=500)
        b = rng.normal(loc=0.0, scale=1.0, size=500)
        result = best_two_sample(a, b)
        # True effect = 0 → P(outside ROPE) should be low
        assert result["p_effect_outside_rope_neg10_pos10"] < 0.5


class TestBestTwoSampleNoNaN:
    def test_no_nan_in_any_field_on_normal_data(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(loc=0.0, scale=1.0, size=30)
        b = rng.normal(loc=0.5, scale=1.0, size=30)
        result = best_two_sample(a, b)
        for key, value in result.items():
            if isinstance(value, float):
                assert not np.isnan(value), f"NaN in field {key!r}"
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, float):
                        assert not np.isnan(v), f"NaN inside list field {key!r}"


class TestBestTwoSampleEdgeCases:
    def test_insufficient_sample_size_returns_sentinel(self):
        result = best_two_sample([1.0], [2.0])
        assert result["method"] == BEST_METHOD_LABEL
        assert result["diff_means_mean"] is None
        assert "error" in result
        assert "insufficient" in result["error"]

    def test_constant_groups_return_sentinel(self):
        result = best_two_sample([1.0, 1.0, 1.0], [2.0, 2.0, 2.0])
        # var_a = 0 AND var_b = 0 → both pooled var = 0 → sentinel
        assert result["diff_means_mean"] is None
        assert "error" in result

    def test_single_constant_group_other_normal_runs(self):
        # If only one group is constant, pooled variance is non-zero
        # so the function should produce a result (var_a = 0 but var_b > 0)
        rng = np.random.default_rng(seed=42)
        a = [5.0, 5.0, 5.0, 5.0, 5.0]
        b = list(rng.normal(loc=10.0, scale=1.0, size=20))
        result = best_two_sample(a, b)
        assert result["diff_means_mean"] is not None
        # diff should be roughly 5
        assert 4.0 < result["diff_means_mean"] < 6.0

    def test_accepts_numpy_arrays(self):
        rng = np.random.default_rng(seed=42)
        a = rng.normal(0, 1, size=30)
        b = rng.normal(0.5, 1, size=30)
        result = best_two_sample(a, b)
        assert result["n_a"] == 30
        assert result["n_b"] == 30

    def test_accepts_python_lists(self):
        result = best_two_sample(
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [2.0, 3.0, 4.0, 5.0, 6.0],
        )
        assert result["n_a"] == 5
        assert result["n_b"] == 5
        assert result["diff_means_mean"] is not None
