"""Block bootstrap (Eq. F.19) and leave-one-fund-out perturbation."""
from __future__ import annotations
import numpy as np

from constants import SEED_BLOCK_BOOT, BLOCK_BOOTSTRAP_LEN


def block_bootstrap(x: np.ndarray, n_replicates: int = 1000,
                    block_size: int = BLOCK_BOOTSTRAP_LEN,
                    seed: int = SEED_BLOCK_BOOT) -> np.ndarray:
    """Hall-Horowitz-Jing (1995) non-overlapping moving block bootstrap.

    Returns an (n_replicates, n_blocks * block_size) array of bootstrap
    series concatenated from randomly-selected non-overlapping blocks.
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    n_blocks = n // block_size
    out = np.empty((n_replicates, n_blocks * block_size))
    for r in range(n_replicates):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        out[r] = np.concatenate([x[s : s + block_size] for s in starts])
    return out


def lofo_perturbation(stat_fn, fund_indices: np.ndarray) -> np.ndarray:
    """Leave-one-fund-out perturbation: returns stat_fn applied with each
    fund individually excluded.

    stat_fn must accept a boolean mask over the fund index axis.
    """
    n = len(fund_indices)
    out = np.empty(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        out[i] = stat_fn(fund_indices[mask])
    return out
