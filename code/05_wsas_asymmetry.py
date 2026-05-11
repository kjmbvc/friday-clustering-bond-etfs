#!/usr/bin/env python3
"""
05_wsas_asymmetry.py
====================
Wrapper-Specificity Asymmetry Statistic (WSAS) -- wrapper-specificity test of
the paper, sec4.3.

For each fund i compute, on the same per-week basis as HCUG:

    p_max_Fri,i  =  fraction of weeks in which Fri attains the WEEKLY MAX premium
    p_min_Fri,i  =  fraction of weeks in which Fri attains the WEEKLY MIN premium
    psi_i        =  p_max_Fri,i  -  p_min_Fri,i              (eq. (psi))

Per-ETF significance
--------------------
Two-sided test of paired-Bernoulli: H0: psi_i = 0 vs H1: psi_i != 0.
Implemented as McNemar-like statistic on (max-on-Fri, min-on-Fri) per week,
with an exact binomial p-value on the discordant pairs (sign test).

Cross-fund summary
------------------
Wilcoxon signed-rank test on {psi_i, i = 1..N_bond} testing H0: median(psi)=0.

Inputs
------
data/processed/premiums.csv

Output
------
output/wsas_results.csv
    ticker, N_weeks, p_max_fri, p_min_fri, psi, p_per_etf, sig_flag
plus a footer row with the cross-fund Wilcoxon test summary
(ticker == '_CROSSFUND_WILCOXON_').

Usage
-----
    python code/05_wsas_asymmetry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon, binomtest
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

REPO = Path(__file__).resolve().parent.parent
PREM = REPO / "data" / "processed" / "premiums.csv"
OUT  = REPO / "output" / "wsas_results.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260101


def per_week_max_min(df_ticker: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (max_on_fri, min_on_fri) -- bool arrays of length n_weeks (>=3 days)."""
    df = df_ticker.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.loc[df["weekday"] <= 4]
    df["week"]    = df["date"].dt.to_period("W-FRI")

    max_fri, min_fri = [], []
    for _, g in df.groupby("week", sort=True):
        K = sorted(set(g["weekday"].astype(int)))
        if len(K) < 3 or 4 not in K:
            # week needs Friday available for the max-vs-min Friday comparison
            continue
        wd_max = int(df.loc[g["premium_pct"].idxmax(), "weekday"])
        wd_min = int(df.loc[g["premium_pct"].idxmin(), "weekday"])
        max_fri.append(wd_max == 4)
        min_fri.append(wd_min == 4)
    return np.asarray(max_fri, dtype=bool), np.asarray(min_fri, dtype=bool)


def sign_test_p(b_max: np.ndarray, b_min: np.ndarray) -> float:
    """Discordant-pair sign test for psi != 0.

    Counts weeks where (max-on-Fri = T, min-on-Fri = F) vs the opposite.
    Under H0, these two counts are exchangeable (Binom(N_disc, 0.5)).
    """
    n_max_only = int((b_max & ~b_min).sum())
    n_min_only = int((~b_max & b_min).sum())
    n_disc = n_max_only + n_min_only
    if n_disc == 0:
        return 1.0
    if HAS_SCIPY:
        return float(binomtest(n_max_only, n_disc, p=0.5, alternative="two-sided").pvalue)
    # numpy fallback (normal approximation)
    z = (n_max_only - 0.5 * n_disc) / np.sqrt(0.25 * n_disc)
    # two-sided
    from math import erfc, sqrt
    return float(erfc(abs(z) / sqrt(2)))


def main() -> int:
    if not PREM.exists():
        sys.exit(f"ERROR: missing {PREM} -- run 03 first.")
    df = pd.read_csv(PREM)

    rows = []
    psi_values = []
    print(f"[05] WSAS asymmetry (psi = p_max,Fri - p_min,Fri):")
    for t, g in df.groupby("ticker", sort=False):
        b_max, b_min = per_week_max_min(g)
        n = len(b_max)
        if n < 30:
            print(f"  [{t}]  too few weeks ({n}) -- skipping")
            continue
        p_max = float(b_max.mean())
        p_min = float(b_min.mean())
        psi   = p_max - p_min
        p_etf = sign_test_p(b_max, b_min)
        rows.append({
            "ticker":    t,
            "N_weeks":   int(n),
            "p_max_fri": round(p_max, 4),
            "p_min_fri": round(p_min, 4),
            "psi":       round(psi, 4),
            "p_per_etf": round(p_etf, 5),
            "sig_flag":  int(p_etf < 0.05),
        })
        if t != "SPY":
            psi_values.append(psi)
        print(f"  [{t}]  N={n:4d}  p_max={p_max:.3f}  p_min={p_min:.3f}  "
              f"psi={psi:+.3f}  p={p_etf:.4f}")

    if not rows:
        sys.exit("ERROR: no fund had enough Friday-containing weeks.")

    # Cross-fund Wilcoxon signed-rank on psi_i (exclude SPY from inference).
    psi_arr = np.asarray(psi_values, dtype=float)
    if HAS_SCIPY and len(psi_arr) >= 5:
        w_stat, w_p = wilcoxon(psi_arr, alternative="two-sided", zero_method="wilcox")
        cross_p = float(w_p)
    else:
        # numpy approximation (signed-rank z under H0)
        ranks = np.argsort(np.argsort(np.abs(psi_arr))) + 1
        signed = ranks * np.sign(psi_arr)
        n = len(psi_arr)
        z = signed.sum() / np.sqrt(n * (n + 1) * (2 * n + 1) / 6)
        from math import erfc, sqrt
        cross_p = float(erfc(abs(z) / sqrt(2)))

    rows.append({
        "ticker":    "_CROSSFUND_WILCOXON_",
        "N_weeks":   len(psi_arr),
        "p_max_fri": round(float(psi_arr.mean()), 4),
        "p_min_fri": np.nan,
        "psi":       round(float(np.median(psi_arr)), 4),
        "p_per_etf": round(cross_p, 6),
        "sig_flag":  int(cross_p < 0.05),
    })

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    n_sig = int(out.loc[out["ticker"].str.startswith("_") == False, "sig_flag"].sum())
    print(f"\n[05] DONE -- wrote {OUT.relative_to(REPO)}")
    print(f"     {n_sig} ETFs reject psi=0 at p<0.05;  cross-fund Wilcoxon p={cross_p:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
