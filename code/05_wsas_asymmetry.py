"""Step 5 — WSAS per fund + cross-fund Wilcoxon (§4.3, Eq. 4, F.24).

For each fund computes:
    p_max,Fri,i  = fraction of weeks where weekly MAX premium falls on Friday
    p_min,Fri,i  = fraction of weeks where weekly MIN premium falls on Friday
    psi_i        = p_max,Fri,i - p_min,Fri,i      (Eq. 4)

Per-fund significance test uses utils.wsas_statistic (paired-Bernoulli z,
Eq. F.24).  Cross-fund Wilcoxon signed-rank uses utils.wsas_wilcoxon_global.

Outputs output/wsas_results.csv.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import TICKERS_ALL_20, OUTPUT_DIR, FRIDAY
from utils import wsas_statistic, wsas_wilcoxon_global
from utils.io import load_premiums


def per_fund_max_min(df_ticker: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (max_weekday, min_weekday) for weeks with >= 3 days INCLUDING Fri."""
    df = df_ticker.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.loc[df["weekday"] <= 4]
    iso = df["date"].dt.isocalendar()
    df["week_id"] = (iso.year * 100 + iso.week).values

    max_wd: list[int] = []
    min_wd: list[int] = []
    for _, sub in df.groupby("week_id", sort=True):
        wds = sorted(sub["weekday"].unique().astype(int))
        if len(wds) < 3 or FRIDAY not in wds:
            continue
        max_wd.append(int(sub.loc[sub["prem"].idxmax(), "weekday"]))
        min_wd.append(int(sub.loc[sub["prem"].idxmin(), "weekday"]))
    return np.asarray(max_wd, dtype=int), np.asarray(min_wd, dtype=int)


def main() -> None:
    df_all = load_premiums()
    rows = []
    psi_per_bond = []
    for tkr in TICKERS_ALL_20:
        df = df_all.loc[df_all["ticker"] == tkr]
        if len(df) < 100:
            print(f"  [{tkr}] skipped (only {len(df)} obs)")
            continue
        max_wd, min_wd = per_fund_max_min(df)
        if len(max_wd) < 30:
            print(f"  [{tkr}] skipped (only {len(max_wd)} usable Fri-weeks)")
            continue
        res = wsas_statistic(max_wd, min_wd)
        rows.append({
            "ticker":    tkr,
            "n_weeks":   int(len(max_wd)),
            "p_max_fri": round(float(res["pi_max"]), 4),
            "p_min_fri": round(float(res["pi_min"]), 4),
            "psi":       round(float(res["psi"]), 4),
            "z":         round(float(res["z"]), 3),
            "p_per_etf": round(float(res["p"]), 5),
            "sig_flag":  int(res["p"] < 0.05),
        })
        if tkr != "SPY":
            psi_per_bond.append(float(res["psi"]))
        print(f"  [{tkr}] N_w={len(max_wd):4d}  p_max={res['pi_max']:.3f}  "
              f"p_min={res['pi_min']:.3f}  psi={res['psi']:+.3f}  p={res['p']:.4f}")

    if not rows:
        sys.exit("ERROR: no per-fund WSAS results.")
    psi_arr = np.asarray(psi_per_bond, dtype=float)
    cross_stat = float("nan")
    cross_p    = float("nan")
    if len(psi_arr) >= 5:
        try:
            cross = wsas_wilcoxon_global(psi_arr)
            cross_stat = float(cross["statistic"])
            cross_p    = float(cross["p"])
        except Exception as exc:  # noqa: BLE001
            print(f"  Wilcoxon failed: {exc}")

    rows.append({
        "ticker":    "_CROSSFUND_WILCOXON_",
        "n_weeks":   int(len(psi_arr)),
        "p_max_fri": round(float(psi_arr.mean()), 4) if len(psi_arr) else float("nan"),
        "p_min_fri": float("nan"),
        "psi":       round(float(np.median(psi_arr)), 4) if len(psi_arr) else float("nan"),
        "z":         round(cross_stat, 3) if not np.isnan(cross_stat) else float("nan"),
        "p_per_etf": round(cross_p, 6) if not np.isnan(cross_p) else float("nan"),
        "sig_flag":  int(cross_p < 0.05) if not np.isnan(cross_p) else 0,
    })

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "wsas_results.csv", index=False)
    bond_rows = out.loc[~out["ticker"].str.startswith("_") & (out["ticker"] != "SPY")]
    n_sig = int(bond_rows["sig_flag"].sum())
    print(f"Step 5 complete: {n_sig} bond ETFs reject psi=0 individually at p<0.05; "
          f"cross-fund Wilcoxon p={cross_p:.4e}")


if __name__ == "__main__":
    main()
