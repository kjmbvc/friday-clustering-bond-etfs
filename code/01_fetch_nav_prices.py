"""Step 1 — fetch daily NAV and unadjusted close per fund.

Sources:
  - Closing prices: yfinance (free, no key required).
  - NAVs:           issuer fund pages (csv export per ticker).

Output: data/raw/<ticker>_close.csv and data/raw/<ticker>_nav.csv.

This script is network-bound; expect ~ 5 minutes wall time on a good
connection.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import TICKERS_ALL_20, DATA_RAW

import pandas as pd

try:
    import yfinance as yf
except ImportError as e:
    raise SystemExit("yfinance not installed; run `pip install yfinance` first.") from e


YF_SUFFIX = {"XBB": "XBB.TO", "ZAG": "ZAG.TO", "VAB": "VAB.TO",
             "IUSU": "IUSU.L", "AGGH": "AGGH.L", "IBGS": "IBGS.L", "IS04": "IS04.L"}


def yf_symbol(t: str) -> str:
    return YF_SUFFIX.get(t, t)


def fetch_close(ticker: str) -> pd.DataFrame:
    """Daily close from yfinance, 2002-01-01 onwards.

    Handles yfinance's MultiIndex-columns output (returned for single-ticker
    requests in newer versions) by flattening to a plain `close` column.
    Returns an empty DataFrame[date, close] when yfinance has no data
    for the symbol (e.g. AGGH.L, IS04.L are delisted on Yahoo).
    """
    sym = yf_symbol(ticker)
    df = yf.download(sym, start="2002-01-01", end="2026-12-31",
                     progress=False, auto_adjust=False, threads=False)
    if df is None or len(df) == 0:
        return pd.DataFrame({"date": [], "close": []})
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if "Close" not in df.columns:
        return pd.DataFrame({"date": [], "close": []})
    out = df[["Close"]].rename(columns={"Close": "close"}).reset_index()
    out = out.rename(columns={"Date": "date"})
    return out[["date", "close"]]


def fetch_nav_placeholder(ticker: str) -> pd.DataFrame:
    """Placeholder NAV from a 5-business-day moving average of close.

    Real issuer NAV requires manual download from the fund's product page;
    see docs/REPLICATION_NOTES.md.  When `data/raw/<TICKER>_nav_issuer.csv`
    exists with columns [date, nav] this script does NOT overwrite it.
    """
    df = fetch_close(ticker).copy()
    if len(df) == 0:
        return pd.DataFrame({"date": [], "nav": [], "nav_source": []})
    df["nav"] = df["close"].rolling(5, min_periods=1).mean()
    df["nav_source"] = "ma5_proxy"
    return df[["date", "nav", "nav_source"]]


def main() -> None:
    for tkr in TICKERS_ALL_20:
        out_close = DATA_RAW / f"{tkr}_close.csv"
        out_nav   = DATA_RAW / f"{tkr}_nav.csv"
        if not out_close.exists():
            print(f"  [{tkr}] fetching close...")
            df = fetch_close(tkr)
            if len(df) == 0:
                print(f"  [{tkr}] yfinance has no data; skipping (likely delisted)")
                continue
            df.to_csv(out_close, index=False)
            time.sleep(0.5)  # rate-limit
        if not out_nav.exists():
            issuer = DATA_RAW / f"{tkr}_nav_issuer.csv"
            if issuer.exists():
                print(f"  [{tkr}] using issuer NAV from {issuer.name}")
                pd.read_csv(issuer).to_csv(out_nav, index=False)
            else:
                print(f"  [{tkr}] fetching NAV (5-day MA proxy)...")
                df = fetch_nav_placeholder(tkr)
                if len(df) == 0:
                    continue
                df.to_csv(out_nav, index=False)
    print("Step 1 complete.")


if __name__ == "__main__":
    main()
