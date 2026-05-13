"""Multicollinearity and influence diagnostics (Eq. F.9, F.10, F.12)."""
from __future__ import annotations
import numpy as np


def vif(X: np.ndarray) -> np.ndarray:
    """Eq. (F.9) Variance Inflation Factor per predictor."""
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    out = np.empty(p)
    for j in range(p):
        Xj = np.delete(X, j, axis=1)
        x  = X[:, j]
        beta_j, *_ = np.linalg.lstsq(Xj, x, rcond=None)
        e = x - Xj @ beta_j
        ss_tot = np.sum((x - x.mean()) ** 2)
        if ss_tot == 0:
            out[j] = np.inf
            continue
        R2 = 1.0 - np.sum(e ** 2) / ss_tot
        out[j] = 1.0 / (1.0 - R2) if R2 < 1.0 else np.inf
    return out


def cooks_distance(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Eq. (F.10) Cook's distance D_i."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    H = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
    MSE = float(np.sum(e ** 2) / max(n - p, 1))
    return (e ** 2 / (p * MSE)) * (H / (1.0 - H) ** 2)


def condition_number(X: np.ndarray) -> float:
    """Eq. (F.12) condition number of X'X via eigenvalue ratio."""
    X = np.asarray(X, dtype=float)
    eigs = np.linalg.eigvalsh(X.T @ X)
    eigs = eigs[eigs > 0]
    return float(np.sqrt(eigs.max() / eigs.min()))
