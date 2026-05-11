#!/usr/bin/env python3
"""
01_fetch_nav_prices.py
======================
Download daily unadjusted closing prices for the 19 bond ETFs (+ SPY equity
benchmark) via yfinance. Produce a placeholder NAV series (5-day MA of close)
when issuer-published NAV is not provided locally.

Issuer NAV (production):
    Place issuer-published NAV CSVs at  data/raw/<TICKER>_nav_issuer.csv
    with columns: date, nav  (one row per business day).
    Issuer fund-page URLs are listed in docs/REPLICATION_NOTES.md.

Inputs
------
data/fund_metadata.csv                 # 20 rows: 19 bond ETFs + SPY
data/raw/<TICKER>_nav_issuer.csv       # OPTIONAL per-ticker issuer NAV

Outputs
-------
data/raw/<TICKER>_close.csv            # date, close
data/raw/<TICKER>_nav.csv              # date, nav, nav_source  (issuer | ma5_proxy)
data/raw/_fetch_log.csv                # ticker, status, n_rows, source

Usage
-----
    python code/01_fetch_nav_prices.py [--start 2002-01-01] [--end 2026-04-30]

Random seed: not used here (no stochastic operations).
Runtime: ~3-5 min on broadband (one yfinance request per ticker).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    sys.exit("ERROR: yfinance required.  pip install yfinance==0.2.40")

# ---------------------------------------------------------------------------
REPO   = Path(__file__).resolve().parent.parent
META   = REPO / "data" / "fund_metadata.csv"
RAW    = REPO / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# Map metadata-ticker -> yfinance-ticker (Yahoo uses regional suffixes).
YF_SUFFIX = {
    "XBB":  "XBB.TO",   # Toronto Stock Exchange
    "ZAG":  "ZAG.TO",
    "VAB":  "VAB.TO",
    "IUSU": "IUSU.L",   # London Stock Exchange (UCITS)
    "AGGH": "AGGH.L",
    "IBGS": "IBGS.L",
    "IS04": "IS04.L",
}


def yf_symbol(ticker: str) -> str:
    return YF_SUFFIX.get(ticker, ticker)


def fetch_one(ticker: str, start: str, end: str, retries: int = 3) -> pd.DataFrame | None:
    """Return DataFrame[date, close] (unadjusted) or None on failure."""
    sym = yf_symbol(ticker)
    for k in range(retries):
        try:
            df = yf.download(
                sym, start=start, end=end,
                progress=False, auto_adjust=False, threads=False,
            )
            if df is None or len(df) == 0:
                time.sleep(1.5)
                continue
            df = df.reset_index()
            # yfinance can return MultiIndex columns when a single ticker is requested.
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ["_".join([str(c) for c in col if c]).strip() for col in df.columns]
            close_col = next(
                (c for c in df.columns if "Close" in c and "Adj" not in c),
                next((c for c in df.columns if "Close" in c), None),
            )
            if close_col is None:
                return None
            out = df[["Date", close_col]].rename(columns={close_col: "close", "Date": "date"})
            out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
            return out
        except Exception as exc:  # noqa: BLE001
            print(f"  [{ticker}] retry {k+1}/{retries}: {exc}")
            time.sleep(2.0)
    return None


def nav_from_issuer_or_proxy(ticker: str, close_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Return (nav_df, source).  Issuer file overrides 5-day MA proxy."""
    issuer_path = RAW / f"{ticker}_nav_issuer.csv"
    if issuer_path.exists():
        nav = pd.read_csv(issuer_path, parse_dates=["date"])
        nav["date"] = pd.to_datetime(nav["date"]).dt.strftime("%Y-%m-%d")
        nav = nav[["date", "nav"]].dropna()
        nav["nav_source"] = "issuer"
        return nav, "issuer"
    # Fallback: 5-business-day rolling mean of close as crude NAV proxy.
    nav = close_df.copy()
    nav["nav"] = nav["close"].rolling(5, min_periods=1).mean()
    nav["nav_source"] = "ma5_proxy"
    return nav[["date", "nav", "nav_source"]], "ma5_proxy"


def main(start: str, end: str) -> int:
    if not META.exists():
        sys.exit(f"ERROR: missing {META}")
    meta = pd.read_csv(META)
    tickers = meta["ticker"].tolist()

    log_rows = []
    print(f"[01] Downloading {len(tickers)} symbols from yfinance "
          f"({start} -> {end})...")
    for i, t in enumerate(tickers, 1):
        print(f"  ({i:2d}/{len(tickers)}) {t:5s}  yf={yf_symbol(t):8s}", end=" ")
        df = fetch_one(t, start, end)
        if df is None or len(df) == 0:
            print("FAIL")
            log_rows.append({"ticker": t, "status": "fail", "n_rows": 0, "source": "yfinance"})
            continue
        df.to_csv(RAW / f"{t}_close.csv", index=False)
        nav_df, src = nav_from_issuer_or_proxy(t, df)
        nav_df.to_csv(RAW / f"{t}_nav.csv", index=False)
        log_rows.append({"ticker": t, "status": "ok", "n_rows": len(df), "source": src})
        print(f"OK  n={len(df):5d}  nav={src}")

    log = pd.DataFrame(log_rows)
    log.to_csv(RAW / "_fetch_log.csv", index=False)
    n_ok = (log["status"] == "ok").sum()
    n_issuer = (log["source"] == "issuer").sum()
    print(f"\n[01] DONE -- {n_ok}/{len(tickers)} OK, {n_issuer} with issuer NAV.")
    if n_issuer < len(tickers):
        print(f"     {len(tickers) - n_issuer} ticker(s) using 5-day MA NAV proxy.")
        print(f"     For production: place issuer-NAV CSVs at "
              f"data/raw/<TICKER>_nav_issuer.csv (columns: date,nav).")
    return 0 if n_ok > 0 else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--start", default="2002-01-01")
    p.add_argument("--end",   default="2026-04-30")
    args = p.parse_args()
    sys.exit(main(args.start, args.end))
