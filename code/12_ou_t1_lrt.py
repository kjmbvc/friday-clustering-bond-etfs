"""Step 12 -- v7 OU model + T+1 LRT + panel DiD with wild-cluster bootstrap.

This is the v7 redesign of §5.6.  It runs three layers of evidence:

(1) Per-fund OU model fits:
    - Baseline OU (3 params)
    - Random Walk (1 param)
    - Brownian Bridge (1 param)
    - Alternative: OU + weekday-conditional drift + T+1 break (12 params)

(2) Per-fund LRTs:
    - lrt_weekday_effect  : H_0 constant drift vs H_1 weekday-conditional
    - lrt_t1_break_only   : H_0 weekday drift vs H_1 weekday x T+1
    - Cross-fund chi^2 aggregation via Fisher's method.

(3) Panel DiD (Treated x Post) with wild-cluster bootstrap at fund level.
    - Pre-trend Wald test for parallel-trends assumption.

Outputs
-------
output/ou_t1_lrt_per_fund.csv      per-fund OU coefficients + LRTs
output/ou_t1_lrt_summary.json      headline cross-fund + panel-DiD numbers
"""
from __future__ import annotations
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import OUTPUT_DIR, PREMIUMS_CSV, TICKERS_BOND_19
from utils.io        import load_fund_metadata, load_premiums
from utils.ou_model  import (FundPanel, per_fund_summary,
                              T_PLUS_ONE_DATE, FRIDAY_IDX)
from utils.wild_cluster import (build_friday_panel, panel_did_wild_cluster,
                                 pre_trend_wald)

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def _fisher_combine(p_values: np.ndarray) -> tuple[float, float]:
    """Fisher's combined-p chi^2 = -2 * sum log(p_i)  ~  chi^2_{2k}."""
    from scipy.stats import chi2
    p = np.asarray(p_values, dtype=float)
    p = p[np.isfinite(p) & (p > 0)]
    if len(p) == 0:
        return float("nan"), float("nan")
    chi = -2.0 * float(np.sum(np.log(p)))
    pf  = float(1.0 - chi2.cdf(chi, df=2 * len(p)))
    return chi, pf


def main() -> int:
    print("=" * 72)
    print(f"Step 12 -- v7 OU model + T+1 LRT + panel DiD wild-cluster bootstrap")
    print(f"T+1 event date: {T_PLUS_ONE_DATE.date()}")
    print("=" * 72)

    meta     = load_fund_metadata()
    premiums = load_premiums()

    # ---- (1) per-fund OU fits + LRTs -------------------------------------
    rows = []
    for tkr in TICKERS_BOND_19:
        df_f = premiums[premiums["ticker"] == tkr]
        if len(df_f) == 0:
            print(f"  [{tkr:6s}]  no data")
            continue
        fund = FundPanel.from_premium_series(tkr, df_f)
        if fund.n_obs < 250:
            print(f"  [{tkr:6s}]  n_obs={fund.n_obs} (skip, < 250)")
            continue
        summary = per_fund_summary(fund)
        rows.append(summary)
        print(f"  [{tkr:6s}]  n={fund.n_obs:5d}  "
              f"LR_wd={summary['LR_weekday']:6.2f} (p={summary['p_weekday']:.3f})  "
              f"LR_t1={summary['LR_t1']:5.2f} (p={summary['p_t1']:.3f})  "
              f"deltaFri={summary['delta_T1_fri']:+.4f}")

    pf = pd.DataFrame(rows)
    pf.to_csv(OUTPUT_DIR / "ou_t1_lrt_per_fund.csv", index=False)
    print(f"\n[12] wrote {OUTPUT_DIR/'ou_t1_lrt_per_fund.csv'}")

    # ---- (2) cross-fund Fisher combination -------------------------------
    chi_wd, p_wd = _fisher_combine(pf["p_weekday"].to_numpy())
    chi_t1, p_t1 = _fisher_combine(pf["p_t1"].to_numpy())
    print(f"\n  Fisher combined LR_weekday  : chi2={chi_wd:.1f}  p={p_wd:.4g}")
    print(f"  Fisher combined LR_t1_break : chi2={chi_t1:.1f}  p={p_t1:.4g}")

    # ---- (3) Panel DiD with wild-cluster bootstrap -----------------------
    meta_t = meta.merge(pf[["ticker"]], on="ticker", how="inner")
    treated = meta_t.loc[meta_t["jurisdiction"].isin(["US", "CA"]), "ticker"].tolist()
    print(f"\n  Treated funds  (n={len(treated)}): {treated}")
    ucits = meta_t.loc[meta_t["jurisdiction"] == "IE", "ticker"].tolist()
    print(f"  Control (UCITS, n={len(ucits)}): {ucits}")

    panel = build_friday_panel(premiums, meta_t, treated_tickers=treated,
                                post_start=T_PLUS_ONE_DATE)
    print(f"  panel rows: {len(panel)}  ({panel['ticker'].nunique()} funds, "
          f"{panel['week_id'].nunique()} weeks)")

    wcb = panel_did_wild_cluster(panel, n_replicates=1999, seed=20260101)
    print(f"\n  Panel DiD (Treated x Post):  beta_hat = {wcb.beta_hat:+.4f}")
    print(f"    HC1 t-stat              = {wcb.t_hc1:+.3f}")
    print(f"    wild-cluster bootstrap p = {wcb.p_wild_two_sided:.4f}"
          f"   (B={wcb.n_replicates}, clusters={wcb.n_clusters})")

    # ---- (4) pre-trend Wald test -----------------------------------------
    pre_window_start = T_PLUS_ONE_DATE - pd.DateOffset(months=12)
    pre_window_end   = T_PLUS_ONE_DATE
    pt = pre_trend_wald(panel, pre_window_start, pre_window_end)
    print(f"\n  Pre-trend Wald (12-month PRE window):")
    print(f"    beta_(t x treated) = {pt['beta']:+.4f}  (SE={pt['se']:.4f})")
    print(f"    t = {pt['t']:+.3f}    p = {pt['p']:.4f}    n={pt['n']}")

    # ---- (5) dump JSON summary -------------------------------------------
    summary = {
        "event_date": str(T_PLUS_ONE_DATE.date()),
        "n_funds":    int(len(pf)),
        "cross_fund_LRT": {
            "weekday_chi2":     round(chi_wd, 3),
            "weekday_p_fisher": round(p_wd, 6),
            "t1_break_chi2":    round(chi_t1, 3),
            "t1_break_p_fisher": round(p_t1, 6),
        },
        "panel_did_wild_cluster": {
            "beta_hat":          round(wcb.beta_hat, 4),
            "t_hc1":             round(wcb.t_hc1, 3),
            "se_hc1":            round(wcb.se_hc1, 4),
            "p_wild_two_sided":  round(wcb.p_wild_two_sided, 4),
            "n_obs":             wcb.n_obs,
            "n_clusters":        wcb.n_clusters,
            "n_replicates":      wcb.n_replicates,
        },
        "pre_trend_wald": {
            "beta":  round(float(pt["beta"]), 4) if np.isfinite(pt["beta"]) else None,
            "se":    round(float(pt["se"]),   4) if np.isfinite(pt["se"])   else None,
            "t":     round(float(pt["t"]),    3) if np.isfinite(pt["t"])    else None,
            "p":     round(float(pt["p"]),    4) if np.isfinite(pt["p"])    else None,
            "n":     int(pt["n"]),
        },
        "treated_tickers": treated,
        "control_tickers": ucits,
    }
    (OUTPUT_DIR / "ou_t1_lrt_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[12] wrote {OUTPUT_DIR/'ou_t1_lrt_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
