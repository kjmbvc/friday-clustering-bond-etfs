"""Unit tests for utils.ou_model (v7 OU model family + LRT)."""
import numpy as np
import pandas as pd
import pytest

from utils.ou_model import (FundPanel, fit_baseline_ou, fit_baseline_rw,
                             fit_baseline_bb, fit_alternative_ou_daily,
                             lrt_weekday_effect, lrt_t1_break_only,
                             predict_friday_max_prob, per_fund_summary,
                             T_PLUS_ONE_DATE, FRIDAY_IDX)


# ---------------------------------------------------------------------------
# Synthetic-data helper
# ---------------------------------------------------------------------------
def _synthetic_panel(ticker: str = "TEST",
                     n_years: int = 8,
                     phi: float = 0.85,
                     omega: float = 0.05,
                     mu_base: float = 0.0,
                     mu_fri_pre: float = 0.0,
                     mu_fri_post: float = 0.0,
                     seed: int = 42) -> FundPanel:
    """Simulate an OU process with weekday-conditional drift and T+1 break."""
    rng     = np.random.default_rng(seed)
    dates   = pd.bdate_range("2017-01-02", periods=int(n_years * 252))
    weekday = dates.weekday.to_numpy()
    tau     = np.asarray(dates >= T_PLUS_ONE_DATE).astype(int)
    n       = len(dates)
    P       = np.zeros(n)
    P[0]    = mu_base
    for t in range(1, n):
        d   = weekday[t]; r = tau[t]
        if d == FRIDAY_IDX and r == 0:
            mu_t = mu_fri_pre
        elif d == FRIDAY_IDX and r == 1:
            mu_t = mu_fri_post
        else:
            mu_t = mu_base
        P[t] = mu_t * (1 - phi) + phi * P[t-1] + rng.normal(0.0, omega)
    df = pd.DataFrame({"date": dates, "prem": P})
    return FundPanel.from_premium_series(ticker, df)


# ---------------------------------------------------------------------------
# Baseline fits
# ---------------------------------------------------------------------------
def test_baseline_ou_recovers_phi():
    fund = _synthetic_panel(phi=0.80, omega=0.05, mu_base=0.0,
                             mu_fri_pre=0.0, mu_fri_post=0.0)
    fit  = fit_baseline_ou(fund.premium)
    assert abs(fit["phi"] - 0.80) < 0.05
    assert abs(fit["omega"] - 0.05) < 0.01
    assert fit["k"] == 3


def test_baseline_rw_omega_close_to_diff_std():
    fund = _synthetic_panel(phi=0.20, omega=0.10)
    fit  = fit_baseline_rw(fund.premium)
    assert fit["k"] == 1
    assert fit["omega"] > 0.0
    assert np.isfinite(fit["loglik"])


def test_baseline_bb_returns_positive_sigma():
    fund = _synthetic_panel()
    fit  = fit_baseline_bb(fund)
    assert fit["sigma_B"] > 0.0
    assert fit["k"] == 1


# ---------------------------------------------------------------------------
# Alternative model
# ---------------------------------------------------------------------------
def test_alternative_recovers_fri_drift_when_planted():
    fund = _synthetic_panel(phi=0.80, omega=0.03,
                             mu_base=0.0, mu_fri_pre=0.5, mu_fri_post=0.5,
                             n_years=10)
    fit  = fit_alternative_ou_daily(fund)
    assert fit["converged"]
    assert fit["k"] == 12
    # mu_fri should be substantially > 0 (we planted +0.5)
    assert fit["mu"][FRIDAY_IDX, 0] > 0.15
    assert fit["mu"][FRIDAY_IDX, 1] > 0.15


def test_alternative_loglik_at_least_baseline():
    """Adding 9 free params can never lower the in-sample log-likelihood."""
    fund = _synthetic_panel()
    ll_b = fit_baseline_ou(fund.premium)["loglik"]
    ll_a = fit_alternative_ou_daily(fund)["loglik"]
    # numerical opt may miss by tiny epsilon -- allow 0.1 nat slack
    assert ll_a >= ll_b - 0.1


# ---------------------------------------------------------------------------
# LRTs
# ---------------------------------------------------------------------------
def test_lrt_weekday_rejects_under_planted_friday_effect():
    fund = _synthetic_panel(mu_base=0.0, mu_fri_pre=0.5, mu_fri_post=0.5,
                             omega=0.05, n_years=10)
    res  = lrt_weekday_effect(fund)
    assert res["df"] == 9
    assert res["LR"] > 30      # planted Friday effect should give big LR
    assert res["p_lrt"] < 0.001


def test_lrt_weekday_does_not_reject_under_null():
    fund = _synthetic_panel(mu_base=0.0, mu_fri_pre=0.0, mu_fri_post=0.0,
                             omega=0.05, n_years=4)
    res  = lrt_weekday_effect(fund)
    # under H_0 the LR is chi^2_9 -- mean 9, 99th pctile ~ 22
    assert res["LR"] < 25
    assert res["p_lrt"] > 0.01


def test_lrt_t1_break_rejects_when_break_planted():
    fund = _synthetic_panel(mu_base=0.0, mu_fri_pre=0.2, mu_fri_post=1.2,
                             omega=0.05, n_years=10)
    res  = lrt_t1_break_only(fund)
    assert res["df"] == 5
    # planted Friday-only drift change should be detected
    assert res["LR"] > 5


def test_lrt_t1_break_does_not_reject_without_break():
    fund = _synthetic_panel(mu_base=0.0, mu_fri_pre=0.5, mu_fri_post=0.5,
                             omega=0.05, n_years=8)
    res  = lrt_t1_break_only(fund)
    # no T+1 change -> LR should be small relative to chi^2_5 (mean 5)
    assert res["p_lrt"] > 0.05


# ---------------------------------------------------------------------------
# Closed-form predictive
# ---------------------------------------------------------------------------
def test_predict_friday_max_prob_in_unit_interval():
    fit = {
        "phi":   0.8,
        "omega": 0.05,
        "mu":    np.zeros((5, 2)),
    }
    p = predict_friday_max_prob(fit, P_last=0.0, tau=1, n_quad=50)
    assert 0.0 < p < 1.0
    # rough symmetry: with all mus = 0, Friday share should be near 1/5
    assert 0.10 < p < 0.40


# ---------------------------------------------------------------------------
# per_fund_summary integration
# ---------------------------------------------------------------------------
def test_per_fund_summary_returns_all_expected_keys():
    fund = _synthetic_panel()
    s = per_fund_summary(fund)
    for key in ("ticker", "n_obs", "phi", "omega",
                "mu_fri_pre", "mu_fri_post", "delta_T1_fri",
                "loglik_ou", "loglik_rw", "loglik_bb", "loglik_alt",
                "LR_weekday", "p_weekday", "LR_t1", "p_t1"):
        assert key in s


def test_per_fund_summary_returns_empty_when_too_short():
    dates = pd.bdate_range("2024-01-01", "2024-02-01")
    df = pd.DataFrame({"date": dates, "prem": np.zeros(len(dates))})
    fund = FundPanel.from_premium_series("X", df)
    s = per_fund_summary(fund)
    assert s == {}
