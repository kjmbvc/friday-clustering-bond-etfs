import numpy as np
from utils import wsas_statistic, wsas_wilcoxon_global


def test_wsas_zero_when_symmetric():
    rng = np.random.default_rng(0)
    n = 1000
    max_day = rng.choice(5, size=n, p=[0.2, 0.2, 0.2, 0.2, 0.2])
    min_day = rng.choice(5, size=n, p=[0.2, 0.2, 0.2, 0.2, 0.2])
    res = wsas_statistic(max_day, min_day)
    assert abs(res["psi"]) < 0.1   # close to 0
    assert res["p"] > 0.05         # not significant


def test_wsas_positive_when_max_fri_clustered():
    rng = np.random.default_rng(1)
    n = 1000
    max_day = rng.choice(5, size=n, p=[0.10, 0.10, 0.10, 0.10, 0.60])
    min_day = rng.choice(5, size=n, p=[0.20, 0.20, 0.20, 0.20, 0.20])
    res = wsas_statistic(max_day, min_day)
    assert res["psi"] > 0.3
    assert res["p"] < 0.001


def test_wilcoxon_global_significant_under_planted_asymmetry():
    psi = np.full(19, 0.3) + np.random.randn(19) * 0.05
    g = wsas_wilcoxon_global(psi)
    assert g["p"] < 0.001
