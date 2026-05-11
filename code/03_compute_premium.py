#!/usr/bin/env python3
"""
03_compute_premium.py
=====================
Compute the daily NAV premium series for every fund:

    Prem(i, t) = ( Close(i, t) - NAV(i, t) ) / NAV(i, t) * 100        (basis points)

Inputs
------
data/raw/<TICKER>_close.csv       # date, close
data/raw/<TICKER>_nav.csv         # date, nav, nav_source

Output
------
data/processed/premiums.csv       # long format
    columns: date, ticker, close, nav, nav_source, premium_pct

Usage
-----
    python code/03_compute_premium.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
META = REPO / "data" / "fund_metadata.csv"
RAW  = REPO / "data" / "raw"
PROC = REPO / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

OUT = PROC / "premiums.csv"


def load_one(ticker: str) -> pd.DataFrame | None:
    cpath = RAW / f"{ticker}_close.csv"
    npath = RAW / f"{ticker}_nav.csv"
    if not cpath.exists() or not npath.exists():
        return None
    close = pd.read_csv(cpath)
    nav   = pd.read_csv(npath)
    df = close.merge(nav, on="date", how="inner")
    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = ticker
    # Guard against zero/negative NAV (shouldn't happen but defensive)
    valid = (df["nav"] > 0)
    df = df.loc[valid].copy()
    df["premium_pct"] = (df["close"] - df["nav"]) / df["nav"] * 100.0
    # Reasonable winsorization at +/- 5% premium (extreme outliers usually data errors)
    df.loc[df["premium_pct"].abs() > 5.0, "premium_pct"] = np.nan
    df = df.dropna(subset=["premium_pct"])
    if "nav_source" not in df.columns:
        df["nav_source"] = "unknown"
    return df[["date", "ticker", "close", "nav", "nav_source", "premium_pct"]]


def main() -> int:
    if not META.exists():
        sys.exit(f"ERROR: missing {META} -- run 01 first.")
    meta = pd.read_csv(META)
    tickers = meta["ticker"].tolist()

    frames = []
    for t in tickers:
        df = load_one(t)
        if df is None or len(df) == 0:
            print(f"  [{t}] no data -- skipping (run 01 first)")
            continue
        print(f"  [{t}] n={len(df):5d}  "
              f"mean prem={df['premium_pct'].mean():+.4f}%  "
              f"sd={df['premium_pct'].std():.4f}%")
        frames.append(df)

    if not frames:
        sys.exit("ERROR: no per-ticker data found in data/raw/.  Run 01 first.")
    out = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"])
    out.to_csv(OUT, index=False)
    print(f"\n[03] DONE -- wrote {len(out):,} rows for {out['ticker'].nunique()} "
          f"tickers to {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
