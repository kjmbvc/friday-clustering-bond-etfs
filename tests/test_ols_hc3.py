import numpy as np
from utils import ols_hc3


def test_ols_recovers_true_coefficients():
    np.random.seed(0)
    n, p = 200, 3
    X = np.column_stack([np.ones(n), np.random.randn(n, p - 1)])
    true = np.array([0.5, 1.0, -0.5])
    y = X @ true + np.random.randn(n) * 0.3
    res = ols_hc3(X, y)
    assert np.allclose(res["beta_hat"], true, atol=0.1)


def test_hc3_se_positive_and_finite():
    np.random.seed(1)
    X = np.column_stack([np.ones(50), np.random.randn(50)])
    y = np.random.randn(50)
    res = ols_hc3(X, y)
    assert np.all(res["se_hc3"] > 0)
    assert np.all(np.isfinite(res["se_hc3"]))


def test_hc3_robust_to_heteroskedasticity():
    """Compare HC3 SE to OLS-style sigma^2 (X'X)^{-1} when residuals are heteroskedastic."""
    np.random.seed(2)
    n = 100
    X = np.column_stack([np.ones(n), np.linspace(0, 1, n)])
    sigma_i = 0.5 + X[:, 1]   # heteroskedastic
    y = X @ np.array([0.0, 1.0]) + np.random.randn(n) * sigma_i
    res = ols_hc3(X, y)
    XtX_inv = np.linalg.inv(X.T @ X)
    sigma2 = np.sum((y - X @ res["beta_hat"]) ** 2) / (n - X.shape[1])
    se_classical = np.sqrt(np.diag(sigma2 * XtX_inv))
    # HC3 SE should differ from classical under heteroskedasticity
    assert not np.allclose(res["se_hc3"], se_classical, atol=0.001)
