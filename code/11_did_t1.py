"""Step 11 — T+1 settlement-transition difference-in-differences (§5.6).

Treatment groups (adopted T+1 on 2024-05-28):
    US_Treasury  : IEF, TLT, GOVT
    US_BroadAgg  : AGG, BND, VTEB, MUB
    US_Credit    : LQD, HYG, EMB, VCIT, SPIB
    Canadian     : XBB, ZAG, VAB

Control group (stayed on T+2):
    European_UCITS : IUSU, IBGS

Pre-window  : 2023-05-28 -> 2024-05-27  (12 months)
Post-window : 2024-05-29 -> 2025-05-28  (12 months)

Outcome     : Fri% = 100 * P(MaxPremDay == Fri | week)

Outputs:
    output/did_t1_per_fund.csv     pre/post Fri% + delta per fund
    output/did_t1_group_summary.csv  mean delta per group
    output/did_t1_results.csv      DiD vs UCITS with Welch t-test
    output/did_t1_summary.json     compact JSON for audit harness
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import OUTPUT_DIR
from utils.io import load_fund_metadata, load_premiums
from utils.did import (T1_EVENT_DATE, fri_share_in_window,
                       assign_group, did_versus_ucits)


def main() -> None:
    print("="*64)
    print(f"T+1 difference-in-differences (event {T1_EVENT_DATE})")
    print("="*64)

    meta = load_fund_metadata()
    df_all = load_premiums()

    pre_start  = pd.Timestamp(T1_EVENT_DATE) - pd.DateOffset(months=12)
    pre_end    = pd.Timestamp(T1_EVENT_DATE)
    post_start = pd.Timestamp(T1_EVENT_DATE) + pd.Timedelta(days=1)
    post_end   = post_start + pd.DateOffset(months=12)
    print(f"  pre  : [{pre_start.date()}, {pre_end.date()})")
    print(f"  post : [{post_start.date()}, {post_end.date()})\n")

    rows = []
    for _, m in meta.iterrows():
        tkr = m["ticker"]
        df_f = df_all[df_all["ticker"] == tkr]
        if len(df_f) == 0:
            continue
        pre  = fri_share_in_window(df_f, pre_start,  pre_end)
        post = fri_share_in_window(df_f, post_start, post_end)
        if pre is None or post is None:
            print(f"  [{tkr:6s}]  SKIP (insufficient weeks)")
            continue
        grp = assign_group(m["jurisdiction"], m["benchmark"], tkr)
        pre_pct, n_pre  = pre
        post_pct, n_post = post
        rows.append({
            "ticker":      tkr,
            "group":       grp,
            "pre_fri_pct": round(pre_pct, 2),
            "post_fri_pct": round(post_pct, 2),
            "delta":       round(post_pct - pre_pct, 2),
            "n_pre":       n_pre,
            "n_post":      n_post,
        })
        print(f"  [{tkr:6s}]  group={grp:18s}  "
              f"pre={pre_pct:5.1f}% (Nw={n_pre:2d})  "
              f"post={post_pct:5.1f}% (Nw={n_post:2d})  "
              f"delta={(post_pct-pre_pct):+5.1f}pp")

    per_fund = pd.DataFrame(rows)
    per_fund.to_csv(OUTPUT_DIR / "did_t1_per_fund.csv", index=False)
    print(f"\n[11] wrote {OUTPUT_DIR/'did_t1_per_fund.csv'}")

    # Group-level summary (mean +/- SE within each group)
    grp_summary = (per_fund.groupby("group")
                          .agg(n            = ("ticker", "count"),
                               pre_mean     = ("pre_fri_pct",  "mean"),
                               post_mean    = ("post_fri_pct", "mean"),
                               delta_mean   = ("delta",        "mean"),
                               delta_sd     = ("delta",        "std"))
                          .round(2)
                          .reset_index())
    grp_summary["delta_se"] = (grp_summary["delta_sd"] /
                                np.sqrt(grp_summary["n"])).round(2)
    grp_summary.to_csv(OUTPUT_DIR / "did_t1_group_summary.csv", index=False)
    print(f"[11] wrote {OUTPUT_DIR/'did_t1_group_summary.csv'}")
    print("\nGroup-level summary:")
    print(grp_summary.to_string(index=False))

    # DiD vs European_UCITS control
    did_df = did_versus_ucits(per_fund)
    if len(did_df):
        did_df = did_df.round({"mean_pre_treat":2, "mean_post_treat":2,
                                "mean_pre_ctrl":2, "mean_post_ctrl":2,
                                "delta_treat":2, "delta_ctrl":2,
                                "did":2, "t_welch":3, "p_welch":4})
        did_df.to_csv(OUTPUT_DIR / "did_t1_results.csv", index=False)
        print(f"\n[11] wrote {OUTPUT_DIR/'did_t1_results.csv'}")
        print("\nDifference-in-differences (treatment - UCITS control):")
        print(did_df[["treatment_group", "n_treat", "n_ctrl",
                       "delta_treat", "delta_ctrl",
                       "did", "t_welch", "p_welch"]].to_string(index=False))

        # JSON sidecar for audit harness
        summary = {
            "event_date": str(T1_EVENT_DATE),
            "pre_window":  [str(pre_start.date()),  str(pre_end.date())],
            "post_window": [str(post_start.date()), str(post_end.date())],
            "n_funds_total": int(len(per_fund)),
            "groups": {row["group"]: {
                "n":          int(row["n"]),
                "pre_mean":   float(row["pre_mean"]),
                "post_mean":  float(row["post_mean"]),
                "delta_mean": float(row["delta_mean"]),
                "delta_se":   float(row["delta_se"]) if not pd.isna(row["delta_se"]) else None,
            } for _, row in grp_summary.iterrows()},
            "did_vs_ucits": {row["treatment_group"]: {
                "did":       float(row["did"]),
                "t_welch":   float(row["t_welch"]),
                "p_welch":   float(row["p_welch"]),
                "n_treat":   int(row["n_treat"]),
                "n_ctrl":    int(row["n_ctrl"]),
            } for _, row in did_df.iterrows()},
        }
        (OUTPUT_DIR / "did_t1_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\n[11] wrote {OUTPUT_DIR/'did_t1_summary.json'}")
    else:
        print("\n[11] WARNING: no UCITS funds in sample; cannot compute DiD")


if __name__ == "__main__":
    main()
