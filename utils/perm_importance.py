"""Permutation variable importance (Eq. F.16)."""
from __future__ import annotations
import numpy as np


def permutation_importance(X: np.ndarray, y: np.ndarray,
                           predict_fn, n_perm: int = 100,
                           seed: int = 20260101) -> np.ndarray:
    """Eq. (F.16): Imp_j = R^2_full - E_perm[R^2(X^{(-j)})].

    Args:
        X:           (n, p) design matrix.
        y:           (n,) response.
        predict_fn:  callable X -> y_hat (already-fitted model).
        n_perm:      permutation replications per predictor.
        seed:        RNG seed.

    Returns:
        importance: (p,) array of mean R^2 drop after permuting column j.
    """
    rng = np.random.default_rng(seed)
    n, p = X.shape
    yhat_full = predict_fn(X)
    sse_full = float(np.sum((y - yhat_full) ** 2))
    sst = float(np.sum((y - y.mean()) ** 2))
    R2_full = 1.0 - sse_full / sst

    out = np.empty(p)
    for j in range(p):
        R2_perm = np.empty(n_perm)
        for b in range(n_perm):
            X_p = X.copy()
            X_p[:, j] = rng.permutation(X_p[:, j])
            yh = predict_fn(X_p)
            R2_perm[b] = 1.0 - np.sum((y - yh) ** 2) / sst
        out[j] = R2_full - float(np.mean(R2_perm))
    return out
