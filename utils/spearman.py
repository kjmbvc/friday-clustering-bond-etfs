"""Spearman rho with t-distribution p-value (Eq. F.8)."""
from __future__ import annotations
import numpy as np
from scipy import stats


def spearman_with_t(x: np.ndarray, y: np.ndarray) -> dict:
    """Spearman rho + t-statistic (Eq. F.8).

    t = rho * sqrt((N - 2) / (1 - rho^2)),  t ~ t_{N-2} under H0.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rho, _ = stats.spearmanr(x, y)
    n = len(x)
    if abs(rho) < 1.0 - 1e-12:
        t_stat = float(rho * np.sqrt((n - 2) / (1 - rho ** 2)))
        p = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), n - 2)))
    else:
        t_stat = np.inf if rho > 0 else -np.inf
        p = 0.0
    return {"rho": float(rho), "t": t_stat, "p": p, "n": n}
