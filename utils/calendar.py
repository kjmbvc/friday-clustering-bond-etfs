"""Weekday and holiday-conditioned trading-day utilities (§4.1, Eq. 2)."""
from __future__ import annotations
import numpy as np
import pandas as pd


def weekday_of(timestamps) -> np.ndarray:
    """Return weekday integer array (Mon=0..Fri=4). Saturdays/Sundays ignored."""
    ts = pd.DatetimeIndex(timestamps)
    return ts.weekday.to_numpy()


def get_trading_calendar(market: str = "NYSE", start: str = "2002-01-01",
                         end: str = "2026-12-31") -> pd.DatetimeIndex:
    """Trading-day calendar for the given market.

    Uses pandas-market-calendars when available; falls back to a
    business-day approximation when the package is missing (only
    affects the holiday-conditioning E_d slightly; weekend exclusion
    is exact).
    """
    try:
        import pandas_market_calendars as mcal
        cal = mcal.get_calendar(market)
        sched = cal.schedule(start_date=start, end_date=end)
        return pd.DatetimeIndex(sched.index.normalize())
    except ImportError:
        return pd.bdate_range(start, end)


def trading_weeks(trading_days: pd.DatetimeIndex) -> dict[int, np.ndarray]:
    """Group trading days by ISO calendar week.

    Returns a dict {week_id: weekday_array}; weekday_array contains
    the weekday integers (0..4) of every trading day in that week.
    Weeks with fewer than 3 trading days are dropped (per §4.1).
    """
    iso = trading_days.isocalendar()
    week_id = iso.year * 100 + iso.week
    out: dict[int, np.ndarray] = {}
    for wid, group in trading_days.to_series().groupby(week_id):
        wds = group.dt.weekday.to_numpy()
        if len(wds) >= 3:
            out[int(wid)] = wds
    return out
