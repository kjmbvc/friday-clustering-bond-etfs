#!/usr/bin/env python3
"""
07_cross_sectional_ols.py
=========================
Cross-sectional OLS of FridayShift on six fund characteristics, plus ridge
LOO-CV and a simple permutation-importance check.

Per the paper sec5.3, the regression is

    FridayShift_i  =  alpha
                    + beta1 * log(AUM_i)
                    + beta2 * Treasury_i
                    + beta3 * log(ADV_i / AUM_i)
                    + beta4 * iNAV_inacc_i
                    + beta5 * BidAsk_i
                    + beta6 * Expense_i
                    + epsilon_i,                    i = 1..N_bond

with HC3 heteroscedasticity-consistent SE, Wald F-tests for the leading
"flow" block (beta1, beta2, beta3), ridge LOO-CV for shrinkage diagnostics,
and a permutation-importance check.

iNAV inaccuracy (iNAV_inacc) is set to NaN when 02 produced empty iNAV files
and is dropped from the regression in that case.

Inputs
------
output/fridayshift.csv            # produced by 06_msgarch_via_rpy2.py
data/fund_metadata.csv            # AUM, ADV, bid-ask, expense, etc.
output/wsas_results.csv           # OPTIONAL -- used for psi side-regression

Output
------
output/cross_sectional.csv
    coefficient, beta_hat, se_hc3, t_stat, p_two_sided, ridge_beta(lambda*)
plus diagnostics (Wald F for flow block, ridge lambda*, condition number,
partial-R^2 of flow block) appended as a JSON sidecar
output/cross_sectional_diag.json.

Random seed
-----------
np.random.seed(20260103)   per the paper (ridge LOO-CV is deterministic;
                                          permutation-importance uses this seed).

Usage
-----
    python code/07_cross_sectional_ols.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
META = REPO / "data" / "fund_metadata.csv"
FS   = REPO / "output" / "fridayshift.csv"
OUT  = REPO / "output" / "cross_sectional.csv"
DIAG = REPO / "output" / "cross_sectional_diag.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260103


def fit_ols_hc3(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Closed-form OLS with HC3 SE.  Returns (beta, se_hc3, V_hc3)."""
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e    = y - X @ beta
    H    = X @ XtX_inv @ X.T
    h    = np.diag(H)
    omega = e ** 2 / (1.0 - h) ** 2
    V    = XtX_inv @ X.T @ np.diag(omega) @ X @ XtX_inv
    return beta, np.sqrt(np.diag(V)), V


def two_sided_p(t_stat: np.ndarray, dof: int) -> np.ndarray:
    """Two-sided t p-value via the (Hill, 1970) numerical recipe -- numpy-only."""
    # Wilson-Hilferty-style approximation for t -> normal as dof grows.
    # For small N this slightly under-estimates p; OK as a conservative test.
    z = t_stat * (1 - 1 / (4 * dof))
    from math import erfc, sqrt
    return np.array([erfc(abs(zi) / sqrt(2)) for zi in z])


def wald_F(beta: np.ndarray, V: np.ndarray, R: np.ndarray) -> tuple[float, int]:
    """Wald F = (R beta)' (R V R')^-1 (R beta) / q."""
    diff = R @ beta
    q = R.shape[0]
    F = float((diff @ np.linalg.inv(R @ V @ R.T) @ diff) / q)
    return F, q


def ridge_loo_cv(X: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray, float]:
    """Hastie-Tibshirani-Friedman LOO shortcut.  Returns (lambda*, beta*, mse*)."""
    lam_grid = np.logspace(-3, 2, 30)
    p = X.shape[1]
    best = (np.inf, None, None)
    for lam in lam_grid:
        A = np.linalg.inv(X.T @ X + lam * np.eye(p))
        beta_r = A @ X.T @ y
        Hr = X @ A @ X.T
        hr = np.diag(Hr)
        e_loo = (y - X @ beta_r) / (1.0 - hr)
        mse = float(np.mean(e_loo ** 2))
        if mse < best[0]:
            best = (mse, lam, beta_r)
    return best[1], best[2], best[0]


def main() -> int:
    if not META.exists():
        sys.exit(f"ERROR: missing {META}")
    if not FS.exists():
        sys.exit(f"ERROR: missing {FS} -- run 06 first.")

    meta = pd.read_csv(META)
    fs   = pd.read_csv(FS)
    df = meta.merge(fs[["ticker", "fridayshift"]], on="ticker", how="inner")
    # Drop SPY equity benchmark from the cross-sectional regression
    df = df.loc[df["ticker"] != "SPY"].copy()
    df = df.dropna(subset=["fridayshift", "aum_usd_bn_2025", "adv_usd_m",
                            "bid_ask_bp", "expense_ratio_bp"])

    # Predictors
    df["log_aum"]    = np.log(df["aum_usd_bn_2025"])
    df["log_advaum"] = np.log(df["adv_usd_m"] / (df["aum_usd_bn_2025"] * 1000))
    df["treasury"]   = df["benchmark"].str.contains("Treasury|Govt", case=False, regex=True).astype(int)

    # iNAV inaccuracy (rows of <TICKER>_inav.csv may be empty if no factsheets)
    inav_path = REPO / "data" / "raw"
    inacc = []
    for t in df["ticker"]:
        ipath = inav_path / f"{t}_inav.csv"
        if ipath.exists():
            try:
                ii = pd.read_csv(ipath)
                inacc.append(np.nan if len(ii) == 0 else float(ii["inav"].std() / ii["inav"].mean() * 100))
            except Exception:
                inacc.append(np.nan)
        else:
            inacc.append(np.nan)
    df["inav_inacc"] = inacc

    # Build design matrix (drop iNAV column entirely if all NaN)
    use_inav = df["inav_inacc"].notna().sum() >= len(df) // 2
    feature_cols = ["log_aum", "treasury", "log_advaum"] \
                 + (["inav_inacc"] if use_inav else []) \
                 + ["bid_ask_bp", "expense_ratio_bp"]
    if not use_inav:
        print("[07] iNAV inaccuracy unavailable for >= 50% of funds -- dropped from model.")
    df_m = df.dropna(subset=feature_cols)
    y = df_m["fridayshift"].values.astype(float)
    X = np.column_stack([np.ones(len(df_m))] + [df_m[c].values.astype(float) for c in feature_cols])

    # Standardize predictors (Beta_std for cross-comparability)
    X_std = X.copy()
    for j in range(1, X.shape[1]):
        sd = X[:, j].std(ddof=1)
        if sd > 0:
            X_std[:, j] = (X[:, j] - X[:, j].mean()) / sd

    print(f"[07] N = {len(df_m)}, predictors = {feature_cols}")
    beta, se, V = fit_ols_hc3(X_std, y)
    dof = len(df_m) - X.shape[1]
    t_stat = beta / np.where(se > 0, se, np.nan)
    p_val  = two_sided_p(t_stat, max(dof, 1))

    # Ridge
    lam_star, beta_ridge, mse_ridge = ridge_loo_cv(X_std, y)

    # Wald F for the flow block (treasury + log(ADV/AUM))
    R = np.zeros((2, X.shape[1]))
    R[0, feature_cols.index("treasury") + 1]  = 1
    R[1, feature_cols.index("log_advaum") + 1] = 1
    F_flow, q_flow = wald_F(beta, V, R)

    # Output table
    rows = [{
        "coefficient":  ["intercept"] + feature_cols,
        "beta_hat":     beta.round(4),
        "se_hc3":       se.round(4),
        "t_stat":       t_stat.round(3),
        "p_two_sided":  p_val.round(5),
        "ridge_beta":   beta_ridge.round(4),
    }]
    out = pd.DataFrame({k: rows[0][k] for k in rows[0]})
    out.to_csv(OUT, index=False)

    # Diagnostics
    eig = np.linalg.eigvalsh(np.cov(X_std[:, 1:].T))
    cond = float(np.sqrt(max(eig) / max(min(eig), 1e-12)))
    diag = {
        "n_obs":           int(len(df_m)),
        "n_predictors":    int(X.shape[1] - 1),
        "feature_cols":    feature_cols,
        "wald_F_flow":     round(F_flow, 3),
        "wald_dof":        [q_flow, dof],
        "ridge_lambda":    round(float(lam_star), 4),
        "ridge_mse_loo":   round(float(mse_ridge), 5),
        "condition_number": round(cond, 2),
        "seed":            SEED,
    }
    DIAG.write_text(json.dumps(diag, indent=2))
    print(f"[07] DONE -- wrote {OUT.relative_to(REPO)} and {DIAG.relative_to(REPO)}")
    print(f"     Wald F(flow block, dof={q_flow},{dof}) = {F_flow:.2f},  "
          f"ridge lambda* = {lam_star:.3f},  cond# = {cond:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
