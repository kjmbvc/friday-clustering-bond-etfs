"""Wild-cluster bootstrap for panel DiD inference.

The headline T+1 claim in v7 of the paper (README v7.2) is

    H_0 : beta_DiD = 0      vs    H_1 : beta_DiD != 0

estimated as the interaction coefficient in the per-fund-week
panel regression

    Fri_indicator_{i,w} = alpha_i + gamma_w + beta * (Treated_i x Post_w) + eps_{i,w},

where Fri_indicator = 1{MaxPremDay_{i,w} = Fri}.

With n_funds ~ 17 and possibly correlated errors within fund (the same
fund's Fri-indicator is autocorrelated week-to-week), the asymptotic
HC1 SE understates uncertainty.  The wild-cluster bootstrap
(Cameron-Gelbach-Miller 2008) draws Rademacher weights w_g in {-1, +1}
at the *cluster* (fund) level and recomputes beta_hat on each
bootstrap replicate; the two-sided p-value is the share of replicates
whose |t_b| exceeds the observed |t_obs|.

Implemented NumPy-only (no scipy/statsmodels) so it runs in the same
environment as the rest of the pipeline.

Reference
---------
Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2008).
"Bootstrap-Based Improvements for Inference with Clustered Errors."
Review of Economics and Statistics 90(3): 414-427.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Per-fund-week panel construction
# ---------------------------------------------------------------------------
def build_friday_panel(premiums: pd.DataFrame,
                       universe:  pd.DataFrame,
                       treated_tickers: Iterable[str],
                       post_start: pd.Timestamp) -> pd.DataFrame:
    """Per-fund-week panel with Friday indicator + Treated x Post interaction.

    Parameters
    ----------
    premiums : DataFrame with columns date, ticker, prem.
    universe : metadata DataFrame keyed on ticker (used only for filter to
                the analysis sample).
    treated_tickers : iterable of tickers in the *treated* group.
    post_start : start date of the post-event window.

    Returns
    -------
    DataFrame with columns
        ticker, week_id, is_fri, treated, post, treat_x_post
    where one row per (ticker, week_id).
    """
    df = premiums[premiums["ticker"].isin(universe["ticker"])].copy()
    iso = pd.DatetimeIndex(df["date"]).isocalendar()
    df["week_id"] = (iso.year * 100 + iso.week).values
    df["weekday"] = pd.DatetimeIndex(df["date"]).weekday

    rows = []
    for (tkr, wid), grp in df.groupby(["ticker", "week_id"]):
        if len(grp) < 3:
            continue
        idx = grp["prem"].idxmax()
        d_max = int(grp.loc[idx, "weekday"])
        wk_start = grp["date"].min()
        rows.append({
            "ticker":   tkr,
            "week_id":  int(wid),
            "wk_start": wk_start,
            "is_fri":   int(d_max == 4),
        })
    panel = pd.DataFrame(rows)
    panel["treated"]      = panel["ticker"].isin(treated_tickers).astype(int)
    panel["post"]         = (panel["wk_start"] >= post_start).astype(int)
    panel["treat_x_post"] = panel["treated"] * panel["post"]
    return panel


# ---------------------------------------------------------------------------
# Two-way fixed-effects within transformation
# ---------------------------------------------------------------------------
def _demean_two_way(y: np.ndarray, X: np.ndarray,
                    fund_id: np.ndarray, week_id: np.ndarray,
                    max_iter: int = 100, tol: float = 1e-10
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Iteratively demean by fund + week to absorb two-way FE."""
    y = y.astype(float).copy()
    X = X.astype(float).copy()
    for _ in range(max_iter):
        y_old = y.copy()
        for g in (fund_id, week_id):
            ser = pd.Series(y).groupby(g).transform("mean").to_numpy()
            y = y - ser
            for j in range(X.shape[1]):
                ser_x = pd.Series(X[:, j]).groupby(g).transform("mean").to_numpy()
                X[:, j] = X[:, j] - ser_x
        if np.max(np.abs(y - y_old)) < tol:
            break
    return y, X


# ---------------------------------------------------------------------------
# Panel DiD point estimate + wild-cluster bootstrap
# ---------------------------------------------------------------------------
@dataclass
class WildClusterResult:
    beta_hat:           float
    se_hc1:             float
    t_hc1:              float
    p_wild_two_sided:   float
    n_obs:              int
    n_clusters:         int
    n_replicates:       int


def panel_did_wild_cluster(panel: pd.DataFrame,
                           n_replicates: int = 1999,
                           seed: int = 20260101) -> WildClusterResult:
    """Panel DiD with wild-cluster bootstrap at fund level.

    Model:
        is_fri_{i,w} = alpha_i + gamma_w + beta * treat_x_post_{i,w} + eps_{i,w}

    beta is estimated by within-transformation (two-way demean) then OLS
    on the demeaned panel.  Wild-cluster bootstrap draws Rademacher
    cluster weights and refits beta on each replicate.
    """
    y_raw = panel["is_fri"].to_numpy(dtype=float)
    X_raw = panel[["treat_x_post"]].to_numpy(dtype=float)
    fund_codes, _ = pd.factorize(panel["ticker"])
    week_codes, _ = pd.factorize(panel["week_id"])

    y_dm, X_dm = _demean_two_way(y_raw, X_raw, fund_codes, week_codes)
    XtX_inv    = 1.0 / float(X_dm.T @ X_dm)
    beta_hat   = float(XtX_inv * (X_dm.T @ y_dm))
    resid      = y_dm - X_dm.flatten() * beta_hat

    # HC1 sandwich SE on the demeaned regression:
    #   Var(beta) = (X'X)^-1 * sum(X_i^2 eps_i^2) * (X'X)^-1 * n/(n-1)
    n         = len(y_dm)
    meat      = float((X_dm.flatten() ** 2 * resid ** 2).sum())
    var_hc1   = XtX_inv * meat * XtX_inv * n / (n - 1)
    se_hc1    = float(np.sqrt(var_hc1))
    t_obs     = beta_hat / se_hc1

    # Wild-cluster bootstrap (WB-R: bootstrap under H_0 imposed at beta=0).
    # Generate y* = X*0 + resid* and refit beta_b; compare |t_b| to |t_obs|.
    rng       = np.random.default_rng(seed)
    n_funds   = int(fund_codes.max() + 1)
    # Restricted residuals: regression of y_dm on a zero-coefficient vector,
    # so the restricted residual equals y_dm itself.
    resid_R   = y_dm.copy()
    abs_t_b   = np.empty(n_replicates)
    for b in range(n_replicates):
        w_g        = rng.choice([-1.0, 1.0], size=n_funds)
        y_star     = resid_R * w_g[fund_codes]
        beta_b     = XtX_inv * float(X_dm.T @ y_star)
        resid_b    = y_star - X_dm.flatten() * beta_b
        meat_b     = float((X_dm.flatten() ** 2 * resid_b ** 2).sum())
        var_b      = XtX_inv * meat_b * XtX_inv * n / (n - 1)
        se_b       = float(np.sqrt(var_b))
        t_b        = beta_b / se_b if se_b > 0 else 0.0
        abs_t_b[b] = abs(t_b)

    p_value = float((1.0 + np.sum(abs_t_b >= abs(t_obs))) / (1.0 + n_replicates))
    return WildClusterResult(
        beta_hat         = beta_hat,
        se_hc1           = se_hc1,
        t_hc1            = float(t_obs),
        p_wild_two_sided = p_value,
        n_obs            = int(n),
        n_clusters       = int(n_funds),
        n_replicates     = int(n_replicates),
    )


# ---------------------------------------------------------------------------
# Pre-trend Wald (parallel-trends check)
# ---------------------------------------------------------------------------
def pre_trend_wald(panel: pd.DataFrame,
                   pre_start: pd.Timestamp,
                   pre_end:   pd.Timestamp) -> dict:
    """Linear pre-trend test: regress is_fri on time x Treated within the
    PRE window only.  beta = 0 under parallel trends.
    """
    pre = panel[(panel["wk_start"] >= pre_start) & (panel["wk_start"] < pre_end)].copy()
    if len(pre) == 0:
        return {"beta": np.nan, "se": np.nan, "t": np.nan, "p": np.nan, "n": 0}
    # Normalise time to weeks since pre_start to keep numerics tame
    pre["t_weeks"] = ((pre["wk_start"] - pre_start).dt.days / 7.0).astype(float)
    pre["t_x_treat"] = pre["t_weeks"] * pre["treated"]
    # Within-transformation by fund (absorb alpha_i)
    y   = pre["is_fri"].to_numpy(dtype=float)
    X   = pre[["t_weeks", "t_x_treat"]].to_numpy(dtype=float)
    fc, _ = pd.factorize(pre["ticker"])
    # Two-way -> here we only demean by fund (no week FE because t is continuous)
    y_dm, X_dm = y - pd.Series(y).groupby(fc).transform("mean").to_numpy(), \
                 X - np.column_stack([pd.Series(X[:, j]).groupby(fc).transform("mean").to_numpy()
                                       for j in range(X.shape[1])])
    XtX = X_dm.T @ X_dm
    Xty = X_dm.T @ y_dm
    try:
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        return {"beta": np.nan, "se": np.nan, "t": np.nan, "p": np.nan, "n": int(len(y))}
    resid = y_dm - X_dm @ beta
    n, k  = X_dm.shape
    sigma2 = float(resid @ resid / (n - k))
    cov    = sigma2 * np.linalg.inv(XtX)
    se     = float(np.sqrt(cov[1, 1]))                      # SE of t_x_treat coefficient
    t      = float(beta[1] / se) if se > 0 else float("nan")
    # asymptotic two-sided p
    from math import erfc, sqrt
    p      = float(erfc(abs(t) / sqrt(2.0))) if np.isfinite(t) else float("nan")
    return {"beta": float(beta[1]), "se": se, "t": t, "p": p, "n": int(n)}
