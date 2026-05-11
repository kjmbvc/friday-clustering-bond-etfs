#!/usr/bin/env python3
"""
10_audit_inputs.py
==================
Compute aggregate statistics that the audit harness references in
`audit/claims_manifest.json` but that no other script produces.

This script is the "glue" between the empirical pipeline and the paper's
prose-level claims.  Add a new aggregate here whenever the paper makes a
claim that doesn't fit cleanly into one cell of an existing CSV.

Inputs
------
output/hcug_results.csv          # from 04
output/wsas_results.csv          # from 05
output/fridayshift.csv           # from 06
output/cross_sectional_diag.json # from 07
output/flow_proxy.csv            # from 08
data/fund_metadata.csv

Outputs
-------
output/spearman_predictors.json    # rho/p/n between FridayShift and 6 predictors
output/aggregate_stats.json        # baselines, sig counts, effect-size ranges
output/subperiod_friday_share.csv  # Friday share by sub-period (DEFERRED ANALYSIS)

Usage
-----
    python code/10_audit_inputs.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import spearmanr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

REPO = Path(__file__).resolve().parent.parent
META  = REPO / "data" / "fund_metadata.csv"
HCUG  = REPO / "output" / "hcug_results.csv"
WSAS  = REPO / "output" / "wsas_results.csv"
FS    = REPO / "output" / "fridayshift.csv"
FLOW  = REPO / "output" / "flow_proxy.csv"
PREM  = REPO / "data" / "processed" / "premiums.csv"

OUT_SPEAR = REPO / "output" / "spearman_predictors.json"
OUT_AGG   = REPO / "output" / "aggregate_stats.json"
OUT_SUBP  = REPO / "output" / "subperiod_friday_share.csv"


def _spearman_numpy(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Numpy fallback for Spearman when scipy missing."""
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4:
        return float("nan"), float("nan")
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rho = np.corrcoef(rx, ry)[0, 1]
    # t-transform p-value
    if abs(rho) < 0.9999:
        t = rho * math.sqrt((n - 2) / (1 - rho * rho))
        # two-sided survival of t -> approximated via normal for n>20, exact via betainc
        if n > 30:
            from math import erfc, sqrt
            p = float(erfc(abs(t) / sqrt(2)))
        else:
            p = float("nan")
    else:
        p = 0.0
    return float(rho), p


def spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    if HAS_SCIPY:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 4:
            return float("nan"), float("nan"), int(mask.sum())
        r, p = spearmanr(x[mask], y[mask])
        return float(r), float(p), int(mask.sum())
    r, p = _spearman_numpy(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    return r, p, int(np.sum(~(np.isnan(np.asarray(x, dtype=float)) | np.isnan(np.asarray(y, dtype=float)))))


def build_spearman() -> dict:
    if not (FS.exists() and META.exists()):
        sys.exit(f"missing {FS} or {META} — run pipeline first")
    fs = pd.read_csv(FS)
    meta = pd.read_csv(META)
    df = meta.merge(fs[["ticker", "fridayshift"]], on="ticker", how="inner")
    df = df.loc[df["ticker"] != "SPY"].copy()

    df["log_aum"]    = np.log(df["aum_usd_bn_2025"])
    df["treasury"]   = df["benchmark"].str.contains("Treasury|Govt", case=False, regex=True).astype(int)
    df["log_advaum"] = np.log(df["adv_usd_m"] / (df["aum_usd_bn_2025"] * 1000))
    df["bid_ask"]    = df["bid_ask_bp"]
    df["expense"]    = df["expense_ratio_bp"]
    # iNAV inacc - read per-ticker from raw if present
    inacc = []
    for t in df["ticker"]:
        path = REPO / "data" / "raw" / f"{t}_inav.csv"
        if path.exists():
            try:
                ii = pd.read_csv(path)
                inacc.append(np.nan if len(ii) == 0 else float(ii["inav"].std() / ii["inav"].mean() * 100))
            except Exception:
                inacc.append(np.nan)
        else:
            inacc.append(np.nan)
    df["inav_inacc"] = inacc

    y = df["fridayshift"].to_numpy(dtype=float)
    out = {}
    for col, label in [("log_aum", "log_aum"), ("treasury", "treasury"),
                        ("log_advaum", "log_advaum"), ("bid_ask", "bid_ask"),
                        ("expense", "expense"), ("inav_inacc", "inav_inacc")]:
        x = df[col].to_numpy(dtype=float)
        r, p, n = spearman(x, y)
        out[label] = {"rho": round(r, 4) if not math.isnan(r) else None,
                       "p_value": round(p, 4) if not math.isnan(p) else None,
                       "n": n}
    return out


def build_aggregates() -> dict:
    if not HCUG.exists():
        sys.exit(f"missing {HCUG} — run pipeline first")
    hcug = pd.read_csv(HCUG)
    bond = hcug.loc[hcug["ticker"] != "SPY"].copy()
    bond["excess_fri_pp"] = bond["fri_pct"] - bond["E_fri_pct"]

    agg = {
        "n_bond_etfs":   int(len(bond)),
        "sig_count_q05": int((bond["q_FDR"] < 0.05).sum()),
        "sig_count_q01": int((bond["q_FDR"] < 0.01).sum()),
        "baseline_E_fri_pct": round(float(bond["E_fri_pct"].mean()), 2),
        "excess_fri_pp_min": round(float(bond["excess_fri_pp"].min()), 2),
        "excess_fri_pp_max": round(float(bond["excess_fri_pp"].max()), 2),
        "fri_pct_median": round(float(bond["fri_pct"].median()), 2),
    }
    # US/non-US strata from fund_metadata.csv
    if META.exists():
        meta = pd.read_csv(META)
        merged = bond.merge(meta[["ticker", "jurisdiction"]], on="ticker", how="left")
        us = merged.loc[merged["jurisdiction"] == "US", "fri_pct"]
        nonus = merged.loc[merged["jurisdiction"] != "US", "fri_pct"]
        agg["us_median_fri_pct"] = round(float(us.median()), 2) if len(us) else None
        agg["nonus_median_fri_pct"] = round(float(nonus.median()), 2) if len(nonus) else None
        agg["us_sig_count"] = int(((merged["jurisdiction"] == "US") & (merged["q_FDR"] < 0.05)).sum())
        agg["nonus_sig_count"] = int(((merged["jurisdiction"] != "US") & (merged["q_FDR"] < 0.05)).sum())
    if WSAS.exists():
        wsas = pd.read_csv(WSAS)
        bw = wsas.loc[~wsas["ticker"].str.startswith("_") & (wsas["ticker"] != "SPY")]
        agg["psi_min"]  = round(float(bw["psi"].min()), 4)
        agg["psi_max"]  = round(float(bw["psi"].max()), 4)
        agg["psi_mean"] = round(float(bw["psi"].mean()), 4)
        agg["psi_sig_count"] = int(bw["sig_flag"].sum())
        # Means of p_max_fri / p_min_fri in PERCENT (csv stores fractions)
        agg["wsas_p_max_fri_mean_pct"] = round(float(bw["p_max_fri"].mean()) * 100, 2)
        agg["wsas_p_min_fri_mean_pct"] = round(float(bw["p_min_fri"].mean()) * 100, 2)
        agg["wsas_p_max_fri_min_pct"] = round(float(bw["p_max_fri"].min()) * 100, 2)
        agg["wsas_p_max_fri_max_pct"] = round(float(bw["p_max_fri"].max()) * 100, 2)
        agg["wsas_p_min_fri_min_pct"] = round(float(bw["p_min_fri"].min()) * 100, 2)
        agg["wsas_p_min_fri_max_pct"] = round(float(bw["p_min_fri"].max()) * 100, 2)
        wilcox = wsas.loc[wsas["ticker"] == "_CROSSFUND_WILCOXON_"]
        if len(wilcox):
            agg["wsas_wilcoxon_p"] = float(wilcox.iloc[0]["p_per_etf"])
    return agg


def build_subperiod() -> pd.DataFrame:
    """Friday share by sub-period for US bond ETFs.  Mirrors paper sec5.7."""
    if not PREM.exists():
        return pd.DataFrame()
    prem = pd.read_csv(PREM, parse_dates=["date"])
    meta = pd.read_csv(META)
    us_bond_tickers = meta.loc[(meta["jurisdiction"] == "US") & (meta["ticker"] != "SPY"), "ticker"].tolist()

    subperiods = [
        ("2002-2009", "2002-01-01", "2009-12-31"),
        ("2010-2014", "2010-01-01", "2014-12-31"),
        ("2015-2019", "2015-01-01", "2019-12-31"),
        ("2020-2026", "2020-01-01", "2026-12-31"),
    ]
    rows = []
    for sub_id, start, end in subperiods:
        df = prem.loc[(prem["date"] >= start) & (prem["date"] <= end)
                       & prem["ticker"].isin(us_bond_tickers)].copy()
        if len(df) == 0:
            continue
        df["weekday"] = df["date"].dt.weekday
        df = df.loc[df["weekday"] <= 4]
        df["week"] = df["date"].dt.to_period("W-FRI")
        fri_shares = []
        for t in us_bond_tickers:
            sub = df.loc[df["ticker"] == t]
            wk_max = sub.loc[sub.groupby("week")["premium_pct"].idxmax()]
            if len(wk_max) < 20:
                continue
            fri_shares.append((wk_max["weekday"] == 4).mean() * 100)
        if fri_shares:
            rows.append({
                "subperiod": sub_id,
                "start": start, "end": end,
                "n_us_funds": len(fri_shares),
                "fri_pct_median": round(float(np.median(fri_shares)), 2),
                "fri_pct_mean":   round(float(np.mean(fri_shares)),   2),
                "fri_pct_min":    round(float(np.min(fri_shares)),    2),
                "fri_pct_max":    round(float(np.max(fri_shares)),    2),
            })
    return pd.DataFrame(rows)


def main() -> int:
    OUT_SPEAR.parent.mkdir(parents=True, exist_ok=True)
    sp = build_spearman()
    OUT_SPEAR.write_text(json.dumps(sp, indent=2), encoding="utf-8")
    print(f"[10] wrote {OUT_SPEAR.relative_to(REPO)}")
    for k, v in sp.items():
        print(f"     {k:>14s}:  rho={v['rho']}  p={v['p_value']}  n={v['n']}")

    agg = build_aggregates()
    OUT_AGG.write_text(json.dumps(agg, indent=2), encoding="utf-8")
    print(f"[10] wrote {OUT_AGG.relative_to(REPO)}")
    for k, v in agg.items():
        print(f"     {k:>22s}:  {v}")

    sub = build_subperiod()
    if len(sub):
        sub.to_csv(OUT_SUBP, index=False)
        print(f"[10] wrote {OUT_SUBP.relative_to(REPO)} ({len(sub)} sub-periods)")
        for _, r in sub.iterrows():
            print(f"     {r['subperiod']}:  median Fri% = {r['fri_pct_median']}  "
                  f"(n_funds={r['n_us_funds']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
