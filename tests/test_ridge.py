import numpy as np
from utils import ridge_loocv


def test_ridge_lambda_zero_recovers_ols():
    np.random.seed(0)
    n, p = 100, 5
    X = np.column_stack([np.ones(n), np.random.randn(n, p - 1)])
    y = X @ np.arange(p, dtype=float) + np.random.randn(n) * 0.1
    rr = ridge_loocv(X, y, lambdas=np.array([1e-8, 1.0, 100.0]))
    ols_beta = np.linalg.lstsq(X, y, rcond=None)[0]
    assert np.allclose(rr["betas"][0], ols_beta, atol=1e-3)


def test_ridge_loo_mse_positive():
    np.random.seed(1)
    X = np.column_stack([np.ones(80), np.random.randn(80, 3)])
    y = np.random.randn(80)
    rr = ridge_loocv(X, y)
    assert np.all(rr["mse_loo"] > 0)
    assert np.isfinite(rr["lambda_star"])


def test_ridge_lambda_grows_with_noise():
    """Optimal LOO lambda should be larger when signal/noise ratio is small."""
    np.random.seed(2)
    n, p = 200, 5
    X = np.column_stack([np.ones(n), np.random.randn(n, p - 1)])
    y_high = X @ np.arange(p, dtype=float) + np.random.randn(n) * 0.1
    y_low  = X @ np.arange(p, dtype=float) + np.random.randn(n) * 5.0
    rr_high = ridge_loocv(X, y_high)
    rr_low  = ridge_loocv(X, y_low)
    assert rr_low["lambda_star"] >= rr_high["lambda_star"]
