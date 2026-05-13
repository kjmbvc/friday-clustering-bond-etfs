"""Unit tests for utils.did (T+1 DiD primitives)."""
import numpy as np
import pandas as pd

from utils.did import (assign_group, welch_t, did_versus_ucits,
                       fri_share_in_window, T1_EVENT_DATE)


# ---------------------------------------------------------------------------
# assign_group
# ---------------------------------------------------------------------------

def test_assign_group_us_treasury():
    assert assign_group("US", "US Treasury 7-10Y", "IEF") == "US_Treasury"
    assert assign_group("US", "20+Y Treasury",     "TLT") == "US_Treasury"
    assert assign_group("US", "US Treasury all",   "GOVT") == "US_Treasury"


def test_assign_group_us_broadagg():
    assert assign_group("US", "US Aggregate", "AGG") == "US_BroadAgg"
    assert assign_group("US", "US Municipal", "MUB") == "US_BroadAgg"


def test_assign_group_us_credit():
    assert assign_group("US", "IG Corporate", "LQD") == "US_Credit"
    assert assign_group("US", "EM Sovereign", "EMB") == "US_Credit"
    assert assign_group("US", "HY Corporate", "HYG") == "US_Credit"


def test_assign_group_canadian_and_ucits():
    assert assign_group("CA", "FTSE Canada Universe", "XBB") == "Canadian"
    assert assign_group("IE", "ICE BofA US Corp",    "IUSU") == "European_UCITS"


def test_assign_group_equity_benchmark():
    assert assign_group("US", "S&P 500", "SPY") == "Equity_Benchmark"


# ---------------------------------------------------------------------------
# welch_t
# ---------------------------------------------------------------------------

def test_welch_t_identical_means_not_significant_at_5pct():
    """Under H0 the p-value should be non-significant most of the time.
    Using a large sample to drive sampling noise down."""
    rng = np.random.default_rng(0)
    a = rng.normal(5.0, 1.0, 500)
    b = rng.normal(5.0, 1.0, 500)
    t, p, df = welch_t(a, b)
    assert p > 0.05                # not significant at conventional threshold
    assert df > 900                # Satterthwaite df should be near n_a + n_b - 2


def test_welch_t_large_diff_significant():
    rng = np.random.default_rng(0)
    a = rng.normal(5.0, 1.0, 30)
    b = rng.normal(7.0, 1.0, 30)
    t, p, df = welch_t(a, b)
    assert t < -3.0
    assert p < 0.001


def test_welch_t_empty_returns_nan():
    t, p, df = welch_t(np.array([]), np.array([1.0, 2.0]))
    assert np.isnan(t)
    assert np.isnan(p)


# ---------------------------------------------------------------------------
# fri_share_in_window
# ---------------------------------------------------------------------------

def test_fri_share_in_window_pure_friday_clustering():
    # Construct a synthetic fund where Friday always has max premium
    dates = pd.bdate_range("2024-01-01", "2024-06-30")
    rng = np.random.default_rng(42)
    prem = rng.normal(0, 0.05, len(dates))
    # boost Friday premiums
    for i, d in enumerate(dates):
        if d.weekday() == 4:    # Friday
            prem[i] = 5.0
    df = pd.DataFrame({"date": dates, "prem": prem})
    res = fri_share_in_window(df,
                              pd.Timestamp("2024-01-01"),
                              pd.Timestamp("2024-07-01"))
    assert res is not None
    pct, n = res
    assert pct >= 95.0    # Friday should dominate
    assert n >= 20


def test_fri_share_in_window_uniform_close_to_20pct():
    dates = pd.bdate_range("2020-01-01", "2023-12-31")
    rng = np.random.default_rng(0)
    prem = rng.normal(0, 1.0, len(dates))
    df = pd.DataFrame({"date": dates, "prem": prem})
    res = fri_share_in_window(df,
                              pd.Timestamp("2020-01-01"),
                              pd.Timestamp("2024-01-01"))
    assert res is not None
    pct, n = res
    # 4 years uniform: Friday share should be near 20% +/- 5 pp
    assert 15.0 < pct < 28.0
    assert n > 150


def test_fri_share_short_window_returns_none():
    dates = pd.bdate_range("2024-05-01", "2024-05-15")   # only ~2 weeks
    df = pd.DataFrame({"date": dates, "prem": np.zeros(len(dates))})
    assert fri_share_in_window(df,
                                pd.Timestamp("2024-05-01"),
                                pd.Timestamp("2024-05-15")) is None


# ---------------------------------------------------------------------------
# did_versus_ucits
# ---------------------------------------------------------------------------

def test_did_versus_ucits_returns_per_group_rows():
    rows = [
        {"ticker": "IEF",  "group": "US_Treasury",    "pre_fri_pct": 23.0, "post_fri_pct": 26.0, "delta": +3.0, "n_pre": 52, "n_post": 52},
        {"ticker": "TLT",  "group": "US_Treasury",    "pre_fri_pct": 19.0, "post_fri_pct": 25.0, "delta": +6.0, "n_pre": 52, "n_post": 52},
        {"ticker": "IUSU", "group": "European_UCITS", "pre_fri_pct": 21.0, "post_fri_pct": 25.0, "delta": +4.0, "n_pre": 52, "n_post": 52},
        {"ticker": "IBGS", "group": "European_UCITS", "pre_fri_pct": 34.0, "post_fri_pct": 38.0, "delta": +4.0, "n_pre": 52, "n_post": 52},
    ]
    df = pd.DataFrame(rows)
    out = did_versus_ucits(df)
    assert len(out) == 1
    r = out.iloc[0]
    assert r["treatment_group"] == "US_Treasury"
    assert abs(r["did"] - (4.5 - 4.0)) < 1e-9    # treat delta 4.5 - ctrl delta 4.0
    assert r["n_treat"] == 2
    assert r["n_ctrl"] == 2


def test_did_returns_empty_when_no_ucits():
    rows = [
        {"ticker": "IEF", "group": "US_Treasury", "pre_fri_pct": 23.0, "post_fri_pct": 26.0, "delta": +3.0, "n_pre": 52, "n_post": 52},
    ]
    df = pd.DataFrame(rows)
    out = did_versus_ucits(df)
    assert len(out) == 0


# ---------------------------------------------------------------------------
# event-date sanity
# ---------------------------------------------------------------------------

def test_event_date_is_may_28_2024():
    """The US T+1 settlement transition was 2024-05-28 (Tuesday)."""
    assert T1_EVENT_DATE.year  == 2024
    assert T1_EVENT_DATE.month == 5
    assert T1_EVENT_DATE.day   == 28
