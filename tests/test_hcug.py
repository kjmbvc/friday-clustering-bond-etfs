import numpy as np
from utils import hcug_test
from utils.permutation import _expected_counts, _g_statistic


def test_expected_counts_uniform_5():
    """When every week has all 5 weekdays, E_d = T/5 for each d."""
    K_w = [np.array([0, 1, 2, 3, 4])] * 100
    E = _expected_counts(K_w)
    assert np.allclose(E, 20.0)


def test_g_statistic_zero_when_uniform():
    """Empirical = expected => G = 0."""
    N = np.array([20, 20, 20, 20, 20], dtype=float)
    E = np.array([20, 20, 20, 20, 20], dtype=float)
    assert abs(_g_statistic(N, E)) < 1e-10  # exact zero up to numerical precision


def test_hcug_returns_pvalue_below_one_for_extreme():
    """When all weekly maxima fall on Friday, p_perm should be tiny."""
    K_w = [np.array([0, 1, 2, 3, 4])] * 100
    max_day = np.full(100, 4, dtype=int)
    res = hcug_test(max_day, K_w, n_perm=500, seed=20260101)
    assert res["fri_share"] == 1.0
    assert res["p_perm"] < 0.05
