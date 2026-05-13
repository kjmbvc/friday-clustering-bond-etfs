import numpy as np
from utils import bh_fdr


def test_bh_fdr_classic_example():
    """Eight hypotheses example from Benjamini-Hochberg (1995)."""
    p = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.060, 0.074, 0.205])
    rejected, q = bh_fdr(p, alpha=0.05)
    assert rejected.sum() == 2  # k* = max{k : p_(k) <= (k/m)*alpha} = 2 for this vector
    assert q[0] < 0.01           # smallest p has small q


def test_bh_fdr_no_rejections_when_all_large():
    p = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
    rejected, _ = bh_fdr(p, alpha=0.05)
    assert rejected.sum() == 0


def test_bh_fdr_q_values_monotone():
    np.random.seed(0)
    p = np.sort(np.random.uniform(0, 1, 50))
    _, q = bh_fdr(p, alpha=0.10)
    # q-values must be non-decreasing in p
    assert np.all(np.diff(q) >= -1e-10)
