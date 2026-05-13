"""Step 3 — compute Prem(i, t) per fund per day (Eq. 1).

Reads data/raw/<ticker>_{close,nav}.csv, joins on date, computes
Prem(i, t) = (Close - NAV) / NAV * 100, writes long-format CSV to
data/processed/premiums.csv.

Robust to missing tickers (delisted on yfinance: AGGH, IS04 sometimes).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import TICKERS_ALL_20, DATA_RAW, PREMIUMS_CSV


def compute_premium_per_fund(ticker: str) -> pd.DataFrame | None:
    """Eq. (1): Prem(i, t) = (Close - NAV) / NAV * 100."""
    cpath = DATA_RAW / f"{ticker}_close.csv"
    npath = DATA_RAW / f"{ticker}_nav.csv"
    if not cpath.exists() or not npath.exists():
        return None
    close = pd.read_csv(cpath, parse_dates=["date"])
    nav   = pd.read_csv(npath, parse_dates=["date"])
    df = close.merge(nav, on="date", how="inner")
    if "nav" not in df.columns or "close" not in df.columns or len(df) == 0:
        return None
    valid = df["nav"] > 0
    df = df.loc[valid].copy()
    df["prem"] = (df["close"] - df["nav"]) / df["nav"] * 100.0
    df.loc[df["prem"].abs() > 5.0, "prem"] = np.nan
    df = df.dropna(subset=["prem"])
    df["ticker"] = ticker
    return df[["date", "ticker", "prem"]]


def main() -> None:
    rows = []
    for tkr in TICKERS_ALL_20:
        out = compute_premium_per_fund(tkr)
        if out is None or len(out) == 0:
            print(f"  [{tkr}] missing close/nav -- skipping")
            continue
        rows.append(out)
        print(f"  [{tkr}] {len(out)} obs  mean prem={out['prem'].mean():+.4f}%  sd={out['prem'].std():.4f}%")
    if not rows:
        sys.exit("ERROR: no per-ticker data found.  Run code/01 first.")
    PREMIUMS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(rows).sort_values(["ticker", "date"]).to_csv(PREMIUMS_CSV, index=False)
    print(f"Step 3 complete -> {PREMIUMS_CSV}")


if __name__ == "__main__":
    main()
