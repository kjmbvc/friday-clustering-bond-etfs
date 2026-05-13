"""WSAS — Wrapper-Specificity Asymmetry Statistic (Eq. 4, F.24)."""
from __future__ import annotations
import numpy as np
from scipy import stats

from constants import FRIDAY, PERMUTATION_REPS, SEED_PERMUTATION


def wsas_statistic(maxprem_day: np.ndarray, minprem_day: np.ndarray,
                   target_weekday: int = FRIDAY) -> dict:
    """Eq. (4): psi_i = p_max,Fri,i - p_min,Fri,i, with paired-Bernoulli SE.

    Args:
        maxprem_day, minprem_day: int arrays of length n_w (per fund),
            weekday (0..4) of weekly max and min premium.
        target_weekday: defaults to Friday (4).
    """
    n = len(maxprem_day)
    pi_max = float(np.mean(maxprem_day == target_weekday))
    pi_min = float(np.mean(minprem_day == target_weekday))
    psi = pi_max - pi_min

    # joint frequency for paired-Bernoulli covariance (Eq. F.24)
    pi_joint = float(np.mean((maxprem_day == target_weekday) &
                             (minprem_day == target_weekday)))
    cov = pi_joint - pi_max * pi_min
    var_psi = (pi_max * (1 - pi_max) + pi_min * (1 - pi_min) - 2 * cov) / n

    if var_psi > 0:
        z = psi / np.sqrt(var_psi)
        p_two_sided = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    else:
        z = 0.0
        p_two_sided = 1.0

    return {"psi": psi, "pi_max": pi_max, "pi_min": pi_min,
            "var_psi": var_psi, "z": z, "p": p_two_sided}


def wsas_wilcoxon_global(psi_per_fund: np.ndarray) -> dict:
    """Cross-fund Wilcoxon signed-rank test of H0: median(psi_i) = 0."""
    res = stats.wilcoxon(psi_per_fund, alternative="two-sided",
                         zero_method="pratt")
    return {"statistic": float(res.statistic), "p": float(res.pvalue)}
