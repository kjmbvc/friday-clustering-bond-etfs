"""Data loading utilities (no math here, just I/O)."""
from __future__ import annotations
import pandas as pd

from constants import FUND_METADATA, PREMIUMS_CSV


def load_fund_metadata() -> pd.DataFrame:
    """End-2025 snapshot of the 19 funds + SPY."""
    return pd.read_csv(FUND_METADATA)


def load_premiums() -> pd.DataFrame:
    """Long-format premium series, columns: date, ticker, prem."""
    return pd.read_csv(PREMIUMS_CSV, parse_dates=["date"])
