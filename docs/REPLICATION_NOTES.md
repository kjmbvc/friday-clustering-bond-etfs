# Replication notes

## Order of execution
The numbered prefix (01..09) gives the required order; each script
depends only on the output of earlier-numbered scripts.

## 01_fetch_nav_prices.py  (~ 5 min, network-bound)
yfinance + issuer fund pages -> `data/raw/<ticker>_close.csv` and `_nav.csv`.
The shipped script uses a placeholder for NAV (NAV = close); replace
the `fetch_nav_placeholder` function with real issuer-page scraping
for production use.

## 02_fetch_inav_factsheets.py  (~ 2 min, network-bound)
Daily iNAV from issuer factsheets (2018-2026 sub-sample).
Shipped stub generates a synthetic iNAV.

## 03_compute_premium.py  (< 1 min)
Eq. (1): Prem(i, t) = (Close - NAV) / NAV * 100.
Output: `data/processed/premiums.csv`.

## 04_hcug_test.py  (~ 5 min, permutation-bound)
Eq. (2)-(3) HCUG + (F.5) BH-FDR.  Output: `output/hcug_results.csv`.
Re-implements Table 1 of the paper.

## 05_wsas_asymmetry.py  (< 1 min)
Eq. (4) WSAS + paired-Bernoulli inference + Wilcoxon signed-rank.
Output: `output/wsas_results.csv`.

## 06_msgarch_via_rpy2.py  (~ 30 min, R-bound)
Eq. (F.17)-(F.18) day-dependent MSGARCH via R MSGARCH 2.5 (rpy2).
Falls back to non-parametric Friday-excess-share when rpy2/MSGARCH
are missing (rho = 0.94 to true FridayShift, per Appendix B.5).
Output: `output/fridayshift.csv`.

## 07_cross_sectional_ols.py  (~ 2 min)
Eq. (F.6)-(F.7) OLS + HC3, (F.9) VIF, (F.10) Cook's D, (F.7') Wald F,
(F.11) ridge LOO-CV, (F.16) permutation importance.
Output: `output/{ols, spearman, permutation_importance}.csv`.

## 08_shares_outstanding_flow.py  (< 1 min when shares-outstanding CSVs are present)
Eq. (F.21) creation/redemption proxy.
Output: `output/flow_proxy.csv`.

## 09_make_figures.py  (< 1 min)
Regenerates figA1, figB2, figC1, figC2 PNGs.
Output: `output/figures/`.

## verification/appendix_F_verification.py  (< 5 sec)
NumPy-only closed-form check of every formula above.
Last printed line should be `ALL CHECKS PASS`.

## tests/  (~ 2 min via `make test`)
pytest unit tests with assertions for every math primitive.
