"""HCUG (Eq. 2-3) and Phipson-Smyth permutation p-value (Eq. F.4)."""
from __future__ import annotations
import numpy as np

from constants import SEED_PERMUTATION, PERMUTATION_REPS, FRIDAY


def _expected_counts(K_w_per_week: list[np.ndarray]) -> np.ndarray:
    """Eq. (2): E_d = sum_w 1(d in K_w) / |K_w|."""
    E = np.zeros(5)
    for K_w in K_w_per_week:
        for d in np.unique(K_w):
            E[d] += 1.0 / len(K_w)
    return E


def _g_statistic(N: np.ndarray, E: np.ndarray) -> float:
    """Eq. (3): G = 2 sum_d N_d log(N_d / E_d). Zero counts contribute 0."""
    mask = (N > 0) & (E > 0)
    return float(2.0 * np.sum(N[mask] * np.log(N[mask] / E[mask])))


def hcug_test(maxprem_day_per_week: np.ndarray,
              K_w_per_week: list[np.ndarray],
              n_perm: int = PERMUTATION_REPS,
              seed: int = SEED_PERMUTATION) -> dict:
    """Holiday-Conditioned Uniform G-test (HCUG, §4.2 of paper).

    Args:
        maxprem_day_per_week: int array of length T, weekday of weekly max
                              (0=Mon..4=Fri).
        K_w_per_week:         list of length T, each element is the array
                              of weekdays available in week w.
        n_perm:               permutation replications (default 10,000).
        seed:                 RNG seed.

    Returns:
        dict with keys G, p_perm, fri_share, N_d, E_d.
    """
    assert len(maxprem_day_per_week) == len(K_w_per_week)
    rng = np.random.default_rng(seed)

    E = _expected_counts(K_w_per_week)
    N = np.bincount(maxprem_day_per_week, minlength=5).astype(float)
    G_obs = _g_statistic(N, E)
    fri_share = N[FRIDAY] / N.sum()

    # within-week permutation, VECTORIZED across weeks within each replicate.
    # Mathematically equivalent to a per-week rng.choice loop, but ~100x faster
    # because the inner loop is pushed into numpy.
    T = len(K_w_per_week)
    K_lens = np.array([len(K_w) for K_w in K_w_per_week], dtype=np.int64)
    K_max  = int(K_lens.max()) if T else 1
    # Pad each K_w to K_max with -1 (sentinel; never indexed because idx < len(K_w))
    K_pad = np.full((T, K_max), -1, dtype=np.int8)
    for w, K_w in enumerate(K_w_per_week):
        K_pad[w, : len(K_w)] = np.asarray(K_w, dtype=np.int8)

    G_perm = np.empty(n_perm)
    for b in range(n_perm):
        u  = rng.random(T)
        idx = (u * K_lens).astype(np.int64)
        wd = K_pad[np.arange(T), idx]            # weekday per week, length T
        N_perm = np.bincount(wd, minlength=5).astype(float)
        G_perm[b] = _g_statistic(N_perm, E)

    p_perm = phipson_smyth_pvalue(G_perm, G_obs)
    return {
        "G": G_obs,
        "p_perm": p_perm,
        "fri_share": fri_share,
        "N_d": N,
        "E_d": E,
    }


def phipson_smyth_pvalue(t_perm: np.ndarray, t_obs: float) -> float:
    """Eq. (F.4): p = (1 + #{t_perm >= t_obs}) / (1 + B). Phipson-Smyth (2010)."""
    B = len(t_perm)
    return float((1 + np.sum(t_perm >= t_obs)) / (1 + B))
