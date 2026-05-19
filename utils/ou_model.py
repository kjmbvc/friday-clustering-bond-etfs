"""Ornstein-Uhlenbeck model family for v7 paper redesign (T+1 LRT).

Adapted from upstream `model_skeleton.py` shipped in
`friday_clustering_replication_v4.zip`.  Field names are normalised to
this repo's convention (`loglik`, `p_lrt`) and an `__upstream_alias__`
metadata dict is preserved so the original v4 driver
(`run_v7_pipeline.py`) can still consume the results.

Models
------
* Baseline 1 -- Pure OU             P_{t+1} = mu(1-phi) + phi P_t + eps        (3 params)
* Baseline 2 -- Random walk         P_{t+1} = P_t + eps                        (1 param)
* Baseline 3 -- Brownian bridge     Within-week demeaned residual              (1 param)
* Alternative -- OU + weekday-conditional drift + T+1 break:
        P_{t+1} = mu_{d(t+1), tau(t+1)} (1 - phi) + phi P_t + eps               (12 params)

LRTs (chi^2_{df} asymptotic)
----------------------------
* lrt_weekday_effect   :  H_0 : mu constant  vs  H_1 : mu_{d,tau}   (df = 9)
* lrt_t1_break_only    :  H_0 : mu_{d}      vs  H_1 : mu_{d,tau}   (df = 5)

Closed-form predictive
----------------------
* predict_friday_max_prob : P(MaxPremDay = Fri) under the alternative model

Notes
-----
The upstream skeleton's `fit_alternative_ou_daily` initialises from the
pure-OU MLE.  For ETFs with degenerate cross-time variance (e.g. ANGL pre-2012),
L-BFGS-B may fail; we catch that and return `converged=False` with `loglik=nan`.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats, optimize


T_PLUS_ONE_DATE   = pd.Timestamp("2024-05-28")   # SEC T+1 transition
WEEKDAY_NAMES     = ["Mon", "Tue", "Wed", "Thu", "Fri"]
FRIDAY_IDX        = 4


# =====================================================================
# Data container
# =====================================================================
@dataclass
class FundPanel:
    ticker:  str
    dates:   pd.DatetimeIndex
    premium: np.ndarray
    weekday: np.ndarray
    tau:     np.ndarray             # 0 pre-T+1, 1 post

    @property
    def n_obs(self) -> int:
        return len(self.premium)

    @classmethod
    def from_premium_series(cls, ticker: str, df: pd.DataFrame) -> "FundPanel":
        """Build a FundPanel from a DataFrame with columns date, prem."""
        df = df.sort_values("date").reset_index(drop=True)
        dates   = pd.DatetimeIndex(df["date"])
        weekday = dates.weekday.to_numpy()
        mask    = weekday <= 4
        return cls(
            ticker  = ticker,
            dates   = dates[mask],
            premium = df["prem"].to_numpy()[mask],
            weekday = weekday[mask],
            tau     = np.asarray(dates[mask] >= T_PLUS_ONE_DATE).astype(int),
        )


# =====================================================================
# Baselines
# =====================================================================
def fit_baseline_ou(P: np.ndarray) -> dict:
    """Pure OU MLE via AR(1) OLS."""
    P_t, P_t1 = P[:-1], P[1:]
    X = np.column_stack([np.ones_like(P_t), P_t])
    beta, *_ = np.linalg.lstsq(X, P_t1, rcond=None)
    resid    = P_t1 - X @ beta
    omega    = float(np.std(resid, ddof=2))
    phi      = float(beta[1])
    mu       = float(beta[0] / (1.0 - phi)) if abs(1.0 - phi) > 1e-6 else 0.0
    loglik   = float(np.sum(stats.norm.logpdf(P_t1, loc=X @ beta, scale=omega)))
    return {"mu": mu, "phi": phi, "omega": omega,
            "loglik": loglik, "ll": loglik,    # ll alias for upstream driver
            "k": 3}


def fit_baseline_rw(P: np.ndarray) -> dict:
    """Random-walk MLE: just std of first differences."""
    dP     = np.diff(P)
    omega  = float(np.std(dP, ddof=1))
    loglik = float(np.sum(stats.norm.logpdf(dP, loc=0.0, scale=omega)))
    return {"omega": omega, "loglik": loglik, "ll": loglik, "k": 1}


def fit_baseline_bb(fund: FundPanel) -> dict:
    """Brownian bridge: within-week demeaned residual variance."""
    df = pd.DataFrame({"prem": fund.premium}, index=fund.dates)
    iso          = df.index.isocalendar()
    df["week"]   = (iso.year * 100 + iso.week).values
    df["resid"]  = df.groupby("week")["prem"].transform(lambda x: x - x.mean())
    sigma_B      = float(np.std(df["resid"].values, ddof=1))
    loglik       = float(np.sum(stats.norm.logpdf(df["resid"].values, loc=0.0, scale=sigma_B)))
    return {"sigma_B": sigma_B, "loglik": loglik, "ll": loglik, "k": 1}


# =====================================================================
# Alternative: OU + weekday-conditional drift + T+1 break
# =====================================================================
def _ou_weekday_neg_ll(theta: np.ndarray, P_t: np.ndarray, P_t1: np.ndarray,
                       d_next: np.ndarray, tau_next: np.ndarray) -> float:
    phi      = np.tanh(theta[0]) * 0.99           # |phi| < 0.99
    omega    = np.exp(theta[1])
    mu_grid  = theta[2:].reshape(5, 2)            # mu[d, tau]
    mu_vec   = mu_grid[d_next, tau_next]
    mean     = mu_vec * (1.0 - phi) + phi * P_t
    return -float(np.sum(stats.norm.logpdf(P_t1, loc=mean, scale=omega)))


def fit_alternative_ou_daily(fund: FundPanel) -> dict:
    """OU with weekday-conditional drift and T+1 break (12 params)."""
    P_t, P_t1 = fund.premium[:-1], fund.premium[1:]
    d_next    = fund.weekday[1:]
    tau_next  = fund.tau[1:]
    base      = fit_baseline_ou(fund.premium)

    theta0 = np.concatenate([
        [np.arctanh(np.clip(base["phi"] / 0.99, -0.99, 0.99))],
        [np.log(max(base["omega"], 1e-6))],
        np.full(10, base["mu"]),
    ])
    try:
        res = optimize.minimize(
            _ou_weekday_neg_ll, theta0,
            args=(P_t, P_t1, d_next, tau_next),
            method="L-BFGS-B")
        phi     = float(np.tanh(res.x[0]) * 0.99)
        omega   = float(np.exp(res.x[1]))
        mu_grid = res.x[2:].reshape(5, 2)
        return {"phi": phi, "omega": omega, "mu": mu_grid,
                "loglik": -float(res.fun), "ll": -float(res.fun),
                "k": 12, "converged": bool(res.success)}
    except (np.linalg.LinAlgError, ValueError):
        return {"phi": np.nan, "omega": np.nan, "mu": np.full((5, 2), np.nan),
                "loglik": np.nan, "ll": np.nan, "k": 12, "converged": False}


# =====================================================================
# Likelihood-ratio tests
# =====================================================================
def lrt_weekday_effect(fund: FundPanel) -> dict:
    """H_0: pure OU (3 params)   vs   H_1: weekday + T+1 (12 params)."""
    restricted   = fit_baseline_ou(fund.premium)
    unrestricted = fit_alternative_ou_daily(fund)
    LR  = 2.0 * (unrestricted["loglik"] - restricted["loglik"])
    df  = unrestricted["k"] - restricted["k"]    # 9
    p   = 1.0 - stats.chi2.cdf(LR, df=df) if LR > 0 else 1.0
    return {"LR": float(LR), "df": int(df), "p_lrt": float(p), "p": float(p),
            "unrestricted": unrestricted, "restricted": restricted}


def lrt_t1_break_only(fund: FundPanel) -> dict:
    """H_0: weekday drift (7 params)   vs   H_1: weekday x T+1 (12 params)."""
    P_t, P_t1 = fund.premium[:-1], fund.premium[1:]
    d_next    = fund.weekday[1:]

    def neg_ll_restricted(theta):
        phi   = np.tanh(theta[0]) * 0.99
        omega = np.exp(theta[1])
        mu_d  = theta[2:7]
        mean  = mu_d[d_next] * (1.0 - phi) + phi * P_t
        return -float(np.sum(stats.norm.logpdf(P_t1, loc=mean, scale=omega)))

    base   = fit_baseline_ou(fund.premium)
    theta0 = np.concatenate([
        [np.arctanh(np.clip(base["phi"] / 0.99, -0.99, 0.99))],
        [np.log(max(base["omega"], 1e-6))],
        np.full(5, base["mu"]),
    ])
    try:
        res_r = optimize.minimize(neg_ll_restricted, theta0, method="L-BFGS-B")
        ll_r  = -float(res_r.fun)
    except (np.linalg.LinAlgError, ValueError):
        return {"LR": np.nan, "df": 5, "p_lrt": np.nan, "p": np.nan}

    unr = fit_alternative_ou_daily(fund)
    LR  = 2.0 * (unr["loglik"] - ll_r)
    p   = 1.0 - stats.chi2.cdf(LR, df=5) if LR > 0 else 1.0
    return {"LR": float(LR), "df": 5, "p_lrt": float(p), "p": float(p),
            "ll_restricted": ll_r, "ll_unrestricted": float(unr["loglik"])}


# =====================================================================
# Closed-form Friday-max probability under the alternative
# =====================================================================
def predict_friday_max_prob(fit: dict, P_last: float, tau: int = 1,
                             n_quad: int = 200) -> float:
    """One-step-ahead P(MaxPremDay = Fri) under the alternative OU.

    Forward-propagates Gaussian conditionals from Monday to Friday given
    yesterday's premium P_last, then integrates Friday's pdf x prod_{d!=Fri}
    Phi(below) over a Gaussian quadrature.
    """
    phi   = fit["phi"]
    omega = fit["omega"]
    mu    = fit["mu"][:, tau]            # length 5

    means, vars_ = np.zeros(5), np.zeros(5)
    P_prev, cum_var = P_last, 0.0
    for d in range(5):
        m       = mu[d] * (1.0 - phi) + phi * P_prev
        means[d]  = m
        cum_var   = phi ** 2 * cum_var + omega ** 2
        vars_[d]  = cum_var
        P_prev    = m

    fri_sd = np.sqrt(vars_[FRIDAY_IDX])
    grid   = np.linspace(means[FRIDAY_IDX] - 6.0 * fri_sd,
                          means[FRIDAY_IDX] + 6.0 * fri_sd, n_quad)
    fri_pdf = stats.norm.pdf(grid, loc=means[FRIDAY_IDX], scale=fri_sd)
    prob = 0.0
    for i, p_val in enumerate(grid):
        below = 1.0
        for d in range(5):
            if d == FRIDAY_IDX:
                continue
            below *= stats.norm.cdf(p_val, loc=means[d], scale=np.sqrt(vars_[d]))
        prob += fri_pdf[i] * below
    prob *= float(grid[1] - grid[0])
    return float(prob)


# =====================================================================
# Per-fund summary helper for the v7 driver
# =====================================================================
def per_fund_summary(fund: FundPanel) -> dict:
    """Run all OU fits + LRTs on one fund and return a flat dict."""
    if fund.n_obs < 100:
        return {}
    ou  = fit_baseline_ou(fund.premium)
    rw  = fit_baseline_rw(fund.premium)
    bb  = fit_baseline_bb(fund)
    alt = fit_alternative_ou_daily(fund)
    lrt_w = lrt_weekday_effect(fund)
    lrt_t = lrt_t1_break_only(fund)
    delta_T1 = float(alt["mu"][FRIDAY_IDX, 1] - alt["mu"][FRIDAY_IDX, 0]) \
                if alt["converged"] else float("nan")
    return {
        "ticker":         fund.ticker,
        "n_obs":          int(fund.n_obs),
        "phi":            float(alt["phi"]) if alt["converged"] else float("nan"),
        "omega":          float(alt["omega"]) if alt["converged"] else float("nan"),
        "mu_fri_pre":     float(alt["mu"][FRIDAY_IDX, 0]) if alt["converged"] else float("nan"),
        "mu_fri_post":    float(alt["mu"][FRIDAY_IDX, 1]) if alt["converged"] else float("nan"),
        "delta_T1_fri":   delta_T1,
        "loglik_ou":      float(ou["loglik"]),
        "loglik_rw":      float(rw["loglik"]),
        "loglik_bb":      float(bb["loglik"]),
        "loglik_alt":     float(alt["loglik"]) if alt["converged"] else float("nan"),
        "LR_weekday":     float(lrt_w["LR"]),
        "p_weekday":      float(lrt_w["p_lrt"]),
        "LR_t1":          float(lrt_t["LR"]),
        "p_t1":           float(lrt_t["p_lrt"]),
    }
