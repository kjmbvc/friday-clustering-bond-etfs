# Replication notes

This document walks through every script in `code/` and what to expect.

## Order of execution
The numbered prefix (01, 02, ..., 09) gives the required order;
scripts depend only on the output of earlier-numbered scripts.

## 01_fetch_nav_prices.py
Downloads daily NAV and unadjusted closing prices for the 19 funds
plus SPY benchmark via `yfinance` and issuer fund pages.
Output: `data/raw/<ticker>_nav.csv`, `data/raw/<ticker>_close.csv`.

## 02_fetch_inav_factsheets.py
Daily iNAV for the 2018-2026 sub-sample from issuer factsheet PDFs.
Output: `data/raw/<ticker>_inav.csv`.

## 03_compute_premium.py
Computes Prem(i,t) = (Close - NAV) / NAV * 100 per fund per day.
Output: `data/processed/premiums.csv`.

## 04_hcug_test.py
Holiday-Conditioned Uniform G-test (HCUG, §4.2 of paper).
10,000-replication permutation; BH-FDR at q < 0.05.
Output: `output/hcug_results.csv` (Table 1 of paper).

## 05_wsas_asymmetry.py
Wrapper-Specificity Asymmetry Statistic (WSAS, §4.3).
Output: `output/wsas_results.csv`.

## 06_msgarch_via_rpy2.py
Day-dependent MSGARCH via R MSGARCH 2.5 package.
Slowest script (~ 30 min). Output: `output/fridayshift.csv`.

## 07_cross_sectional_ols.py
Multivariate OLS + HC3 + ridge + fractional logit + LOFO + permutation
importance. Output: `output/cross_sectional.csv`.

## 08_shares_outstanding_flow.py
Daily creation/redemption proxy (12 U.S. funds).
Output: `output/flow_proxy.csv`.

## 09_make_figures.py
Regenerates figA1, figB2, figC1, figC2 PNGs from the output CSVs.
Output: `output/figures/`.

## verification/appendix_F_verification.py
NumPy-only closed-form verification of every numerical result.
Last printed line should be `ALL CHECKS PASS`.

## Random seeds
Hard-coded in each script:
- Permutation: 20260101
- MSGARCH start: 20260102
- Ridge LOO-CV: 20260103
