"""Benjamini-Hochberg FDR (Eq. F.5)."""
from __future__ import annotations
import numpy as np


def bh_fdr(pvalues: np.ndarray, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Eq. (F.5): k* = max{k : p_(k) <= (k/m) alpha}; reject p_(j) for j <= k*.

    Args:
        pvalues: raw two-sided p-values (length m).
        alpha:   FDR level (default 0.05).

    Returns:
        rejected: boolean array of length m.
        q_adj:    BH-adjusted q-values, same order as input.
    """
    p = np.asarray(pvalues, dtype=float)
    m = len(p)
    order = np.argsort(p)
    p_sorted = p[order]

    thresholds = (np.arange(1, m + 1) / m) * alpha
    below = p_sorted <= thresholds
    if not np.any(below):
        k_star = 0
    else:
        k_star = int(np.max(np.where(below)[0]) + 1)

    rejected = np.zeros(m, dtype=bool)
    rejected[order[:k_star]] = True

    # adjusted q-values: cumulative-min from end of (m/k * p_(k))
    raw = (m / np.arange(1, m + 1)) * p_sorted
    raw_cummin = np.minimum.accumulate(raw[::-1])[::-1]
    q = np.zeros(m)
    q[order] = np.clip(raw_cummin, 0.0, 1.0)
    return rejected, q
