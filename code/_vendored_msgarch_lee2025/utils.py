import numpy as np

EPS = 1e-8
S   = 1.0 - 1e-6

HUBER_C   = 3.0
TEMP0     = 2.0
RIDGE_TAU = 0.01

def scad_clip(x, lam=10., a=3.7):
    """Smoothly-Clipped Absolute Deviation (Fan & Li, 2001)."""
    if x <= lam:
        return x
    if x <= a * lam:
        return lam + (x - lam) / (a - 1)
    return 0.5 * (a + 1) * lam

def compute_lam_scad(ret, factor=10.0):
    med = np.median(ret)
    return factor * np.median(np.abs(ret - med))