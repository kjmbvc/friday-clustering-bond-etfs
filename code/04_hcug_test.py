#!/usr/bin/env python3
"""
04_hcug_test.py
===============
Holiday-Conditioned Uniform G-test (HCUG) -- primary test of the paper.

For each fund i and each calendar week w with available days K_w (subset of
{Mon, Tue, Wed, Thu, Fri}), find the weekday on which the fund's NAV premium
attains its weekly maximum.  Under H0 (no day-of-week effect), the maximum
falls on each available day with equal probability 1/|K_w|.

Per-fund test statistic
-----------------------
    G_i = 2 * sum_d  N_{i,d} * log( N_{i,d} / E_{i,d} ),

with the holiday-conditioned expected counts

    E_{i,d} = sum_w  I( d in K_w ) / |K_w|.

p-value
-------
Within-week permutation: for each week, redraw the maximum-day uniformly
from K_w; recompute G; repeat 10,000 times.  Empirical right-tail p with
Phipson-Smyth (+1) correction.

Multiple testing
----------------
Benjamini-Hochberg FDR at q < 0.05 across the 19 funds (SPY excluded from
correction since it is the equity benchmark).

Inputs
------
data/processed/premiums.csv       # produced by 03_compute_premium.py

Output
------
output/hcug_results.csv
    ticker, N_weeks, fri_pct, mon_pct, ..., G_stat, p_perm, q_FDR, sig_flag

Random seed
-----------
np.random.seed(20260101)  per the paper's reproducibility checklist.

Usage
-----
    python code/04_hcug_test.py [--n-perm 10000]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PREM = REPO / "data" / "processed" / "premiums.csv"
OUT  = REPO / "output" / "hcug_results.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri"]
SEED = 20260101


def weekly_max_weekday(df_ticker: pd.DataFrame) -> tuple[list[list[int]], list[int]]:
    """Return (weeks_K_list, max_weekday_per_week) restricted to weeks with >=3 days."""
    df = df_ticker.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday          # 0=Mon ... 4=Fri (5,6 dropped)
    df = df.loc[df["weekday"] <= 4]
    df["week"]    = df["date"].dt.to_period("W-FRI")

    weeks_K: list[list[int]] = []
    max_wd:  list[int] = []
    for _, g in df.groupby("week", sort=True):
        K = sorted(set(g["weekday"].astype(int)))
        if len(K) < 3:
            continue
        idx_max = g["premium_pct"].idxmax()
        wd_max  = int(df.loc[idx_max, "weekday"])
        weeks_K.append(K)
        max_wd.append(wd_max)
    return weeks_K, max_wd


def expected_counts(weeks_K: list[list[int]]) -> np.ndarray:
    """Holiday-conditioned expected counts E_d for d in {0,...,4}."""
    E = np.zeros(5)
    for K in weeks_K:
        contrib = 1.0 / len(K)
        for d in K:
            E[d] += contrib
    return E


def g_statistic(N: np.ndarray, E: np.ndarray) -> float:
    """G = 2 * sum N_d log(N_d / E_d).  Convention 0*log(0/E)=0."""
    g = 0.0
    for n, e in zip(N, E):
        if n > 0 and e > 0:
            g += 2.0 * n * math.log(n / e)
    return float(g)


def permutation_p(weeks_K: list[list[int]], obs_G: float, n_perm: int, rng: np.random.Generator) -> float:
    E = expected_counts(weeks_K)
    perm_G = np.zeros(n_perm)
    # Pre-pick uniformly at random within each week, vectorised per replicate.
    week_arrays = [np.asarray(K, dtype=np.int64) for K in weeks_K]
    for b in range(n_perm):
        N = np.zeros(5, dtype=np.int64)
        for K_arr in week_arrays:
            d = K_arr[rng.integers(0, len(K_arr))]
            N[d] += 1
        perm_G[b] = g_statistic(N.astype(float), E)
    # Phipson-Smyth: (1 + #{perm >= obs}) / (1 + B).  Avoids zero p-values.
    return float((1 + np.sum(perm_G >= obs_G)) / (1 + n_perm))


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """Standard BH-FDR.  Returns q-values aligned with input order."""
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    p_s = p[order]
    q_s = p_s * n / (np.arange(n) + 1)
    q_s = np.minimum.accumulate(q_s[::-1])[::-1]
    q   = np.empty_like(q_s)
    q[order] = q_s
    return np.clip(q, 0.0, 1.0)


def main(n_perm: int) -> int:
    if not PREM.exists():
        sys.exit(f"ERROR: missing {PREM} -- run 03 first.")
    df = pd.read_csv(PREM)
    rng = np.random.default_rng(SEED)

    rows = []
    print(f"[04] HCUG G-test (B={n_perm}, seed={SEED}) -- by ticker:")
    for t, g in df.groupby("ticker", sort=False):
        weeks_K, max_wd = weekly_max_weekday(g)
        if len(max_wd) < 30:
            print(f"  [{t}]  too few weeks ({len(max_wd)}) -- skipping")
            continue
        N = np.zeros(5, dtype=float)
        for d in max_wd:
            N[d] += 1
        E = expected_counts(weeks_K)
        G = g_statistic(N, E)
        p = permutation_p(weeks_K, G, n_perm, rng)
        rows.append({
            "ticker":   t,
            "N_weeks":  int(N.sum()),
            **{f"{nm}_pct": round(N[i] / N.sum() * 100.0, 2) for i, nm in enumerate(WEEKDAY_NAMES)},
            **{f"E_{nm}_pct": round(E[i] / E.sum() * 100.0, 2) for i, nm in enumerate(WEEKDAY_NAMES)},
            "G_stat":   round(G, 4),
            "p_perm":   round(p, 5),
        })
        print(f"  [{t}] N={int(N.sum()):4d}  fri%={N[4]/N.sum()*100:5.1f}  "
              f"G={G:7.2f}  p={p:.4f}")

    if not rows:
        sys.exit("ERROR: no fund had enough weeks -- premiums.csv may be empty.")

    out = pd.DataFrame(rows)
    # FDR over the 19 bond ETFs (exclude SPY benchmark from correction).
    bond_mask = out["ticker"] != "SPY"
    q_bond = benjamini_hochberg(out.loc[bond_mask, "p_perm"].values)
    q_full = np.full(len(out), np.nan)
    q_full[bond_mask.values] = q_bond
    out["q_FDR"]    = np.round(q_full, 5)
    out["sig_flag"] = (out["q_FDR"] < 0.05).fillna(False).astype(int)
    out.to_csv(OUT, index=False)

    n_sig = int(out.loc[bond_mask, "sig_flag"].sum())
    print(f"\n[04] DONE -- wrote {OUT.relative_to(REPO)}")
    print(f"     {n_sig}/{int(bond_mask.sum())} bond ETFs significant at q<0.05.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n-perm", type=int, default=10000)
    args = p.parse_args()
    sys.exit(main(args.n_perm))
