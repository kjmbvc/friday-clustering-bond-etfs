"""T+1 settlement-transition difference-in-differences (§5.6 of frl_paper.tex).

The 28 May 2024 U.S. T+1 settlement transition (also adopted by Canada on the
same day) is treated as a quasi-experiment.  European UCITS funds continued
on T+2 and serve as the not-treated control.

Outcome (per fund i, per window):
    Fri%_i = 100 * (#weeks with MaxPremDay_i == Fri) / (#weeks with |K_w| >= 3)

Per-fund DiD: Delta_i = Fri%_i(post) - Fri%_i(pre)
Group-level mean: mean of Delta_i within each group
Difference-in-differences:
    DiD_g = mean(Delta_i in treatment group g) - mean(Delta_i in UCITS control)

Inference: Welch (unequal-variance) two-sample t-test on the Delta_i values.

Notes
-----
* Per-fund pre/post Fri% is a binomial proportion based on ~52 weeks each.
  Standard error per fund: sqrt(p(1-p)/N_w) ~ 6 pp.  Group means average this
  noise across funds.
* With n_UCITS = 2 in our sample, control-group variance is large and the
  DiD test is under-powered.  This module computes the point estimate and
  Welch t-test honestly; the paper text reports both Delta_g (pure treatment
  effect) and DiD_g (UCITS-controlled).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

import numpy as np
import pandas as pd

# T+1 event (US/CA settlement transition; UK/EU stayed on T+2)
T1_EVENT_DATE: date = date(2024, 5, 28)


def fri_share_in_window(df_fund: pd.DataFrame,
                        start: pd.Timestamp,
                        end:   pd.Timestamp,
                        min_weeks: int = 20) -> tuple[float, int] | None:
    """Fraction of weeks (in pct) whose MaxPremDay equals Friday.

    Parameters
    ----------
    df_fund : DataFrame with columns date, prem (one ticker only).
    start, end : window endpoints (inclusive start, exclusive end).
    min_weeks : drop the fund if fewer than this many weeks are available.

    Returns
    -------
    (fri_pct, n_weeks) or None if too few weeks.
    """
    sub = df_fund[(df_fund["date"] >= start) & (df_fund["date"] < end)].copy()
    if len(sub) < 30:
        return None
    iso = pd.DatetimeIndex(sub["date"]).isocalendar()
    sub = sub.assign(week_id=(iso.year * 100 + iso.week).values,
                     wd=pd.DatetimeIndex(sub["date"]).weekday)
    fri, total = 0, 0
    for _, grp in sub.groupby("week_id"):
        if len(grp) < 3:
            continue
        d_max = int(grp.loc[grp["prem"].idxmax(), "wd"])
        if d_max == 4:           # Friday == 4
            fri += 1
        total += 1
    if total < min_weeks:
        return None
    return 100.0 * fri / total, total


def assign_group(jurisdiction: str, benchmark: str, ticker: str) -> str:
    """Map (jurisdiction, benchmark) -> treatment-group label.

    Groups:
      - US_Treasury           : benchmark contains 'Treasury' (incl. GOVT/IEF/TLT)
      - US_BroadAgg           : Aggregate / Municipal indices
      - US_Credit             : IG corporate / HY / EM
      - Canadian              : CA jurisdiction (also adopted T+1)
      - European_UCITS        : IE jurisdiction (CONTROL: stayed T+2)
      - Equity_Benchmark      : SPY (separate reference row)
    """
    if jurisdiction == "CA":
        return "Canadian"
    if jurisdiction == "IE":
        return "European_UCITS"
    if ticker == "SPY":
        return "Equity_Benchmark"
    if jurisdiction == "US":
        bm = benchmark.lower()
        if "treasury" in bm:
            return "US_Treasury"
        if "aggregate" in bm or "municipal" in bm:
            return "US_BroadAgg"
        return "US_Credit"
    return "Other"


@dataclass
class DiDResult:
    """Container for one (treatment group vs UCITS control) DiD result."""
    treatment_group:   str
    n_treat:           int
    n_ctrl:            int
    mean_pre_treat:    float
    mean_post_treat:   float
    mean_pre_ctrl:     float
    mean_post_ctrl:    float
    delta_treat:       float    # post-pre mean within treatment
    delta_ctrl:        float    # post-pre mean within UCITS
    did:               float    # delta_treat - delta_ctrl
    t_welch:           float
    p_welch:           float


def welch_t(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Welch's two-sample t-test on (a - b mean difference).  Returns
    (t, p_two_sided, df_satterthwaite).  Implemented without scipy so
    this module stays NumPy-only.
    """
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan"), float("nan"), float("nan")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    if se == 0:
        return float("nan"), float("nan"), float("nan")
    t = (a.mean() - b.mean()) / se
    df = (va / na + vb / nb) ** 2 / (
        (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    )
    # two-sided p via t-distribution survival; use scipy if available, else normal-approx
    try:
        from scipy.stats import t as t_dist
        p = float(2.0 * t_dist.sf(abs(t), df))
    except ImportError:
        from math import erfc, sqrt
        p = float(erfc(abs(t) / sqrt(2)))
    return float(t), p, float(df)


def did_versus_ucits(per_fund: pd.DataFrame,
                     treatment_groups: Iterable[str] = (
                         "US_Treasury", "US_BroadAgg",
                         "US_Credit", "Canadian")) -> pd.DataFrame:
    """Compute DiD vs UCITS for each treatment group.

    Parameters
    ----------
    per_fund : DataFrame with columns
        ticker, group, pre_fri_pct, post_fri_pct, delta, n_pre, n_post.

    Returns
    -------
    DataFrame, one row per treatment group, columns matching DiDResult.
    """
    if "European_UCITS" not in per_fund["group"].unique():
        return pd.DataFrame()
    ctrl = per_fund[per_fund["group"] == "European_UCITS"]
    out = []
    for grp in treatment_groups:
        sub = per_fund[per_fund["group"] == grp]
        if len(sub) == 0:
            continue
        t, p, _df = welch_t(sub["delta"].values, ctrl["delta"].values)
        out.append(DiDResult(
            treatment_group  = grp,
            n_treat          = int(len(sub)),
            n_ctrl           = int(len(ctrl)),
            mean_pre_treat   = float(sub["pre_fri_pct"].mean()),
            mean_post_treat  = float(sub["post_fri_pct"].mean()),
            mean_pre_ctrl    = float(ctrl["pre_fri_pct"].mean()),
            mean_post_ctrl   = float(ctrl["post_fri_pct"].mean()),
            delta_treat      = float(sub["delta"].mean()),
            delta_ctrl       = float(ctrl["delta"].mean()),
            did              = float(sub["delta"].mean() - ctrl["delta"].mean()),
            t_welch          = t,
            p_welch          = p,
        ).__dict__)
    return pd.DataFrame(out)
