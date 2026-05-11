#!/usr/bin/env python3
"""
08_shares_outstanding_flow.py
=============================
Daily shares-outstanding flow proxy for the 12 U.S. bond ETFs.

We construct the proxy from the change in shares outstanding (delta-S):

    Creation_t   = max( 0, S_t - S_{t-1} )
    Redemption_t = max( 0, S_{t-1} - S_t )

then aggregate to weekly Friday share:

    FridayCreate_i  =  sum_{t in Fri} Creation_{i,t}  /  sum_t Creation_{i,t}

If `yfinance.Ticker.get_shares_full(start, end)` returns daily shares, we use
it directly.  If only periodic snapshots are available (typical for non-U.S.
listings), we treat between-snapshot delta-S as missing.

Inputs
------
data/fund_metadata.csv            # 19 + SPY ticker list
data/raw/_fetch_log.csv           # fetch status from 01

Output
------
output/flow_proxy.csv
    ticker, region, n_obs_days, friday_create_pct, friday_redeem_pct,
    expected_friday_pct
data/raw/<TICKER>_shares.csv      # date, shares_outstanding (cache)

Usage
-----
    python code/08_shares_outstanding_flow.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    sys.exit("ERROR: yfinance required.  pip install yfinance==0.2.40")

REPO = Path(__file__).resolve().parent.parent
META = REPO / "data" / "fund_metadata.csv"
RAW  = REPO / "data" / "raw"
OUT  = REPO / "output" / "flow_proxy.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

YF_SUFFIX = {
    "XBB": "XBB.TO", "ZAG": "ZAG.TO", "VAB": "VAB.TO",
    "IUSU": "IUSU.L", "AGGH": "AGGH.L", "IBGS": "IBGS.L", "IS04": "IS04.L",
}


def yf_symbol(t: str) -> str:
    return YF_SUFFIX.get(t, t)


def fetch_shares(ticker: str, start: str = "2018-01-01",
                 end: str = "2026-04-30") -> pd.DataFrame:
    """Return DataFrame[date, shares_outstanding].  Empty on failure."""
    cache = RAW / f"{ticker}_shares.csv"
    if cache.exists():
        try:
            df = pd.read_csv(cache, parse_dates=["date"])
            if len(df) > 0:
                return df
        except Exception:
            pass
    try:
        sym = yf_symbol(ticker)
        s = yf.Ticker(sym).get_shares_full(start=start, end=end)
        if s is None or len(s) == 0:
            return pd.DataFrame(columns=["date", "shares_outstanding"])
        df = s.reset_index().rename(columns={s.index.name or "index": "date", 0: "shares_outstanding"})
        # Some yfinance versions return a Series
        if "shares_outstanding" not in df.columns:
            df.columns = ["date", "shares_outstanding"]
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df.dropna().sort_values("date").drop_duplicates("date")
        df.to_csv(cache, index=False)
        return df
    except Exception as exc:  # noqa: BLE001
        print(f"  [{ticker}] shares fetch failed: {exc}")
        return pd.DataFrame(columns=["date", "shares_outstanding"])


def friday_share(daily: pd.DataFrame) -> tuple[float, float, int]:
    """Return (friday_create_pct, friday_redeem_pct, n_obs_days)."""
    if len(daily) < 30:
        return float("nan"), float("nan"), len(daily)
    df = daily.sort_values("date").copy()
    df["delta"] = df["shares_outstanding"].diff().fillna(0)
    df["create"] = df["delta"].clip(lower=0)
    df["redeem"] = (-df["delta"]).clip(lower=0)
    df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
    biz = df.loc[df["weekday"] <= 4]
    tot_c = biz["create"].sum()
    tot_r = biz["redeem"].sum()
    fri_c = biz.loc[biz["weekday"] == 4, "create"].sum()
    fri_r = biz.loc[biz["weekday"] == 4, "redeem"].sum()
    return (
        float(fri_c / tot_c * 100.0) if tot_c > 0 else float("nan"),
        float(fri_r / tot_r * 100.0) if tot_r > 0 else float("nan"),
        int(len(biz)),
    )


def expected_friday_pct(dates: pd.Series) -> float:
    """Holiday-conditioned expected Friday share for these business days."""
    if len(dates) == 0:
        return float("nan")
    dt = pd.to_datetime(pd.Series(list(dates)).reset_index(drop=True))
    weeks = dt.dt.to_period("W-FRI")
    df = pd.DataFrame({"date": dt.values, "weekday": dt.dt.weekday.values, "week": weeks.values})
    df = df.loc[df["weekday"] <= 4]
    by_week = df.groupby("week")["weekday"].apply(lambda s: sorted(set(s.astype(int))))
    by_week = by_week[by_week.apply(lambda K: len(K) >= 3)]
    if len(by_week) == 0:
        return float("nan")
    e_fri = float(np.mean([1.0 / len(K) if 4 in K else 0.0 for K in by_week]))
    return e_fri * 100.0


def main() -> int:
    if not META.exists():
        sys.exit(f"ERROR: missing {META}")
    meta = pd.read_csv(META)
    rows = []
    print("[08] Shares-outstanding flow proxy:")
    for _, m in meta.iterrows():
        t = m["ticker"]
        if t == "SPY":
            continue
        df = fetch_shares(t)
        if len(df) == 0:
            print(f"  [{t}]  no shares-outstanding data available")
            rows.append({"ticker": t, "region": m["jurisdiction"],
                          "n_obs_days": 0, "friday_create_pct": float("nan"),
                          "friday_redeem_pct": float("nan"),
                          "expected_friday_pct": float("nan")})
            continue
        fc, fr, n = friday_share(df)
        ef = expected_friday_pct(df["date"])
        rows.append({"ticker": t, "region": m["jurisdiction"],
                      "n_obs_days": n,
                      "friday_create_pct": round(fc, 2) if not np.isnan(fc) else fc,
                      "friday_redeem_pct": round(fr, 2) if not np.isnan(fr) else fr,
                      "expected_friday_pct": round(ef, 2) if not np.isnan(ef) else ef})
        print(f"  [{t}]  n={n:5d}  Fri create={fc:5.2f}%  "
              f"Fri redeem={fr:5.2f}%  E[Fri]={ef:5.2f}%")

    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n[08] DONE -- wrote {OUT.relative_to(REPO)}")
    n_with_data = sum(1 for r in rows if r["n_obs_days"] > 0)
    print(f"     {n_with_data}/{len(rows)} ETFs had usable shares-outstanding series.")
    if n_with_data < len(rows):
        print("     (Non-U.S. listings often expose only periodic snapshots via yfinance;")
        print("      run from the issuer's daily flow CSV for full coverage.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
