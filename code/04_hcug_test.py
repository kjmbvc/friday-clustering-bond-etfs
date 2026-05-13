"""Step 4 — HCUG test per fund + BH-FDR across the family (§4.2, Eq. 2-3, F.5).

Uses utils.hcug_test (the math primitive in utils/permutation.py) plus a
robust groupby-on-week-id construction of (max_weekday, K_w) per week.

Outputs output/hcug_results.csv with columns:
    ticker, n_weeks, fri_pct, E_fri_pct, G_stat, p_perm, q_FDR,
    rejected_q05, sig_flag, sig
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import TICKERS_ALL_20, OUTPUT_DIR, FDR_LEVEL_PRIMARY, FRIDAY
from utils import hcug_test, bh_fdr
from utils.io import load_premiums


def _sig_label(q: float) -> str:
    if pd.isna(q):    return "ref"
    if q < 0.001:     return "***"
    if q < 0.01:      return "**"
    if q < 0.05:      return "*"
    return "n.s."


def per_fund_max_and_Kw(df_ticker: pd.DataFrame) -> tuple[np.ndarray, list[np.ndarray]]:
    """Return (max_weekday_per_week, K_w_list) restricted to weeks with >=3 days."""
    df = df_ticker.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.loc[df["weekday"] <= 4]
    iso = df["date"].dt.isocalendar()
    df["week_id"] = (iso.year * 100 + iso.week).values

    max_per_week: list[int] = []
    K_w_list:     list[np.ndarray] = []
    for _, sub in df.groupby("week_id", sort=True):
        wds = np.sort(sub["weekday"].unique().astype(int))
        if len(wds) < 3:
            continue
        i_max = sub["prem"].idxmax()
        max_per_week.append(int(sub.loc[i_max, "weekday"]))
        K_w_list.append(wds)
    return np.asarray(max_per_week, dtype=int), K_w_list


def main() -> None:
    df_all = load_premiums()
    rows = []
    for tkr in TICKERS_ALL_20:
        df = df_all.loc[df_all["ticker"] == tkr]
        if len(df) < 100:
            print(f"  [{tkr}] skipped (only {len(df)} obs)")
            continue
        max_per_week, K_w = per_fund_max_and_Kw(df)
        if len(max_per_week) < 30:
            print(f"  [{tkr}] skipped (only {len(max_per_week)} usable weeks)")
            continue
        result = hcug_test(max_per_week, K_w)
        rows.append({
            "ticker":    tkr,
            "n_weeks":   int(len(max_per_week)),
            "fri_pct":   round(100.0 * float(result["fri_share"]), 2),
            "G_stat":    round(float(result["G"]), 4),
            "p_perm":    round(float(result["p_perm"]), 5),
            "E_fri_pct": round(100.0 * float(result["E_d"][FRIDAY]) / float(result["E_d"].sum()), 2),
        })
        print(f"  [{tkr}] N_w={len(max_per_week):4d} Fri%={rows[-1]['fri_pct']:5.1f}  "
              f"G={result['G']:6.2f} p_perm={result['p_perm']:.4f}")

    if not rows:
        sys.exit("ERROR: no per-fund HCUG results.")
    out = pd.DataFrame(rows)
    bond_mask = out["ticker"] != "SPY"
    rejected_bond, q_bond = bh_fdr(out.loc[bond_mask, "p_perm"].values,
                                     alpha=FDR_LEVEL_PRIMARY)
    q_full = np.full(len(out), np.nan)
    rejected_full = np.zeros(len(out), dtype=bool)
    q_full[bond_mask.values] = q_bond
    rejected_full[bond_mask.values] = rejected_bond
    out["q_FDR"] = np.round(q_full, 5)
    out["rejected_q05"] = rejected_full
    out["sig_flag"] = rejected_full.astype(int)
    out["sig"] = [_sig_label(qi) for qi in out["q_FDR"]]
    out.to_csv(OUTPUT_DIR / "hcug_results.csv", index=False)
    print(f"Step 4 complete: {int(rejected_bond.sum())}/{int(bond_mask.sum())} "
          f"bond ETFs reject HCUG at q<{FDR_LEVEL_PRIMARY}")


if __name__ == "__main__":
    main()
